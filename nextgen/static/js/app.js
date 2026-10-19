/* NextGenPathashala frontend: all persistent operations use the authenticated Flask API. */
(() => {
  'use strict';
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const csrfToken = $('meta[name="csrf-token"]')?.content || '';
  const rememberedAccountsKey = 'nextgenpathashala.rememberedAccounts.v1';
  const pendingRememberedAccountKey = 'nextgenpathashala.pendingRememberedAccount.v1';

    function getRememberedAccounts() {
      try {
        const accounts = JSON.parse(localStorage.getItem(rememberedAccountsKey) || '[]');
        return Array.isArray(accounts) ? accounts.filter(account => account && typeof account.email === 'string') : [];
      } catch (_) { return []; }
    }

    function renderRememberedAccounts() {
      const section = $('#savedAccounts');
      const list = $('#savedAccountList');
      if (!section || !list) return;
      const accounts = getRememberedAccounts();
      section.hidden = accounts.length === 0;
      list.replaceChildren();
      accounts.forEach(account => {
        const row = document.createElement('div');
        row.className = 'saved-account-row';
        const choose = document.createElement('button');
        choose.type = 'button';
        choose.className = 'saved-account-choice';
        choose.dataset.accountEmail = account.email;
        choose.dataset.accountInstitution = account.institution || '';
        const name = document.createElement('strong');
        name.textContent = account.name || account.email;
        const details = document.createElement('small');
        details.textContent = [account.email, account.institution].filter(Boolean).join(' · ');
        choose.append(name, details);
        const remove = document.createElement('button');
        remove.type = 'button';
        remove.className = 'forget-account';
        remove.dataset.forgetEmail = account.email;
        remove.setAttribute('aria-label', `Forget ${account.email} on this device`);
        remove.title = 'Forget this account on this device';
        remove.textContent = '×';
        row.append(choose, remove);
        list.append(row);
      });
    }

    function bindLoginAccounts() {
      const form = $('#loginForm');
      if (!form) return;
      try { sessionStorage.removeItem(pendingRememberedAccountKey); } catch (_) { /* Storage can be disabled. */ }
      renderRememberedAccounts();
      form.addEventListener('submit', () => {
        try {
          if ($('#rememberAccount')?.checked) {
            sessionStorage.setItem(pendingRememberedAccountKey, $('#email').value.trim().toLowerCase());
          } else {
            sessionStorage.removeItem(pendingRememberedAccountKey);
          }
        } catch (_) { /* Sign-in still works when browser storage is disabled. */ }
      });
      $('#savedAccountList')?.addEventListener('click', event => {
        const remove = event.target.closest('[data-forget-email]');
        if (remove) {
          const accounts = getRememberedAccounts().filter(account => account.email !== remove.dataset.forgetEmail);
          try { localStorage.setItem(rememberedAccountsKey, JSON.stringify(accounts)); } catch (_) { /* Ignore storage errors. */ }
          renderRememberedAccounts();
          return;
        }
        const choice = event.target.closest('[data-account-email]');
        if (!choice) return;
        $('#email').value = choice.dataset.accountEmail;
        $('#institution').value = choice.dataset.accountInstitution;
        $('#rememberAccount').checked = true;
        $('#password').focus();
      });
    }

    function rememberSignedInAccount() {
      let pendingEmail = '';
      try {
        pendingEmail = sessionStorage.getItem(pendingRememberedAccountKey) || '';
        sessionStorage.removeItem(pendingRememberedAccountKey);
      } catch (_) { return; }
      if (!pendingEmail || pendingEmail !== state.user?.email?.toLowerCase()) return;
      const account = {
        name: state.user.name,
        email: state.user.email,
        institution: state.institution?.name || '',
        role: state.user.role,
      };
      const accounts = getRememberedAccounts().filter(item => item.email !== account.email);
      accounts.unshift(account);
      try { localStorage.setItem(rememberedAccountsKey, JSON.stringify(accounts.slice(0, 8))); } catch (_) { /* Sign-in still works when storage is full or disabled. */ }
    }
  const state = { user: null, institution: null, classes: [], users: [], students: [], sessions: [], assignments: [], notices: [], attendanceSession: null, deferredInstall: null };
  // Import state stays in memory only; never persist temporary passwords locally.
  let pendingStudentImportRows = [];
  let lastImportCredentials = [];

  const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
  const firstName = (name = '') => name.trim().split(/\s+/)[0] || 'there';
  const todayLocal = () => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  };
  const dateTimeLocalValue = (d) => {
    const local = new Date(d.getTime() - d.getTimezoneOffset() * 60000);
    return local.toISOString().slice(0, 16);
  };
  const formatDate = (value, opts = { day: 'numeric', month: 'short', year: 'numeric' }) => value ? new Date(value).toLocaleDateString(undefined, opts) : 'No due date';
  const formatTime = (value) => value ? new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—';
  const formatDateTime = (value) => value ? `${formatDate(value, { day: 'numeric', month: 'short' })} · ${formatTime(value)}` : 'No due date';
  const asInitials = (name = '') => name.split(/\s+/).filter(Boolean).slice(0, 2).map(part => part[0]).join('').toUpperCase() || 'N';

  function toast(message, type = 'info') {
    const region = $('#toastRegion');
    if (!region) return;
    const item = document.createElement('div');
    item.className = `toast ${type === 'error' ? 'error' : type === 'success' ? 'success' : ''}`;
    item.textContent = message;
    region.append(item);
    window.setTimeout(() => item.remove(), 4500);
  }

  async function api(path, options = {}) {
    const headers = new Headers(options.headers || {});
    headers.set('Accept', 'application/json');
    headers.set('X-CSRFToken', csrfToken);
    if (options.body !== undefined && !headers.has('Content-Type') && !(typeof FormData !== 'undefined' && options.body instanceof FormData)) headers.set('Content-Type', 'application/json');
    let response;
    try {
      response = await fetch(path, { ...options, headers, credentials: 'same-origin' });
    } catch (error) {
      const status = $('#connectionStatus');
      if (status) { status.classList.add('offline'); status.lastChild.textContent = ' Offline'; }
      throw new Error('Connection failed. Check your internet connection and try again.');
    }
    const status = $('#connectionStatus');
    if (status) { status.classList.toggle('offline', !navigator.onLine); status.lastChild.textContent = navigator.onLine ? ' Connected' : ' Offline'; }
    const contentType = response.headers.get('content-type') || '';
    const data = contentType.includes('application/json') ? await response.json() : {};
    if (response.status === 401) {
      if (location.pathname !== '/login') location.assign('/login');
      throw new Error(data.error || 'Please sign in again.');
    }
    if (!response.ok) throw new Error(data.error || `Request failed (${response.status}).`);
    return data;
  }

  function sectionName(id) {
    return ({ overview: 'Overview', timetable: 'Timetable', attendance: 'Attendance', homework: 'Homework', notices: 'Notices', feedback: 'Feedback', study: 'Study Lab', 'study-buddy': 'Study Buddy', account: 'Account', manage: 'Classes & people' })[id] || 'Overview';
  }
  function goToSection(id) {
    if (!$('#section-' + id)) return;
    $$('.page-section').forEach(section => section.classList.toggle('active', section.id === 'section-' + id));
    $$('.nav-link').forEach(button => button.classList.toggle('active', button.dataset.section === id));
    const title = $('#currentPageName');
    if (title) title.textContent = sectionName(id);
    $('#sidebar')?.classList.remove('mobile-open');
    if (id === 'timetable') loadTimetable($('#timetableDate')?.value || todayLocal()).catch(showError);
    if (id === 'attendance' && state.user?.role === 'student') loadMyAttendance().catch(showError);
    if (id === 'attendance' && state.user?.role !== 'student') loadSessionsForAttendance().catch(showError);
    if (id === 'homework') loadAssignments().catch(showError);
    if (id === 'notices') loadNotices().catch(showError);
    if (id === 'study' || id === 'study-buddy') loadStudyMaterials().catch(showError);
    if (id === 'manage' && state.user?.role === 'admin') loadManagement().catch(showError);
    if (id === 'feedback' && state.user?.role === 'admin') loadFeedback().catch(showError);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
  const showError = (error) => toast(error?.message || 'Something went wrong.', 'error');
  const isStaff = () => ['admin', 'teacher'].includes(state.user?.role);

  function applyRoleVisibility() {
    const role = state.user?.role || '';
    $$('.admin-only').forEach(el => { el.hidden = role !== 'admin'; });
    $$('.staff-only').forEach(el => { el.hidden = !['admin', 'teacher'].includes(role); });
    $$('.student-only').forEach(el => { el.hidden = role !== 'student'; });
    const tab = $('[data-section="manage"]');
    if (tab) tab.hidden = role !== 'admin';
    $('#profileName').textContent = state.user?.name || 'User';
    $('#profileRole').textContent = role || '';
    $('#userAvatar').textContent = asInitials(state.user?.name);
    $('#topAvatar').textContent = asInitials(state.user?.name);
    $('#profileEmail').textContent = state.user?.email || '—';
    $('#profileUserId').textContent = state.user?.id ?? '—';
    $('#profileInstitution').textContent = state.institution?.name || '—';
    $('#profileStudentId').textContent = state.user?.student_id ?? '—';
    $('#profileStudentCode').textContent = state.user?.student_code || '—';
    $$('.student-account-fact').forEach(item => { item.hidden = role !== 'student'; });
    const date = new Date();
    $('#greeting').textContent = `Good ${date.getHours() < 12 ? 'morning' : date.getHours() < 17 ? 'afternoon' : 'evening'}, ${firstName(state.user?.name)}!`;
    $('#todayLabel').textContent = date.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' }).toUpperCase();
  }

  function renderStats(stats = {}) {
    const role = state.user?.role;
    let cards;
    if (role === 'admin') {
      cards = [
        ['♙', 'Students', stats.students ?? 0, 'Student accounts', 'purple'],
        ['✧', 'Teachers', stats.teachers ?? 0, 'Active teacher accounts', 'mint'],
        ['▦', 'Classes & batches', stats.classes ?? 0, 'Groups in your workspace', 'peach'],
        ['◷', "Today's classes", stats.sessions_today ?? 0, 'Scheduled for today', 'blue']
      ];
    } else if (role === 'teacher') {
      cards = [
        ['◷', "Today's classes", stats.sessions_today ?? 0, 'Your teaching schedule', 'purple'],
        ['▤', 'Assignments', stats.assignments ?? 0, 'Across your classes', 'mint'],
        ['▦', 'Classes', stats.classes ?? 0, 'Groups assigned to you', 'peach'],
        ['✦', 'Notices', state.notices.length, 'Visible updates', 'blue']
      ];
    } else {
      cards = [
        ['◷', "Today's classes", stats.sessions_today ?? 0, 'On your timetable', 'purple'],
        ['▤', 'Assignments', stats.assignments ?? 0, 'Recent class work', 'mint'],
        ['▦', 'My classes', stats.classes ?? 0, 'Enrolled groups', 'peach'],
        ['✦', 'Notices', state.notices.length, 'Visible updates', 'blue']
      ];
    }
    $('#statsGrid').innerHTML = cards.map(([icon, label, value, note, color]) => `<article class="stat-card"><span class="stat-icon ${color}">${icon}</span><span class="stat-label">${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong><span class="stat-note">${escapeHtml(note)}</span></article>`).join('');
  }

  function renderSessionItem(item, attendanceAction = false) {
    const status = item.status || 'scheduled';
    return `<div class="list-item"><div class="time-pill">${escapeHtml(formatTime(item.starts_at))}<small>${escapeHtml(formatTime(item.ends_at))}</small></div><div class="list-content"><strong>${escapeHtml(item.subject)} <span class="status-tag ${escapeHtml(status)}">${escapeHtml(status)}</span></strong><p>${escapeHtml(item.class_name)}${item.room ? ` · ${escapeHtml(item.room)}` : ''}</p><p>${escapeHtml(item.teacher_name || 'Unassigned teacher')}</p></div>${attendanceAction && isStaff() && status !== 'cancelled' ? `<button class="button button-soft attend-session" data-session-id="${item.id}">Register</button>` : ''}${state.user?.role === 'admin' && status === 'scheduled' ? `<button class="icon-button cancel-session" data-session-id="${item.id}" title="Cancel session" aria-label="Cancel session">×</button>` : ''}</div>`;
  }
  function renderAssignmentItem(item, studentMode = state.user?.role === 'student') {
    const due = item.due_at ? formatDateTime(item.due_at) : 'No deadline';
    const submission = item.submission;
    const isOverdue = item.due_at && new Date(item.due_at) < new Date() && !submission;
    if (studentMode) {
      return `<article class="notice-card"><div class="notice-meta"><span>${escapeHtml(item.class_name)} · ${escapeHtml(item.subject)}</span><span class="status-tag ${submission ? 'submitted' : isOverdue ? 'overdue' : 'pending'}">${submission ? 'submitted' : isOverdue ? 'overdue' : 'pending'}</span></div><h3>${escapeHtml(item.title)}</h3><p>${escapeHtml(item.instructions || 'No extra instructions provided.')}</p><div class="notice-footer">Due: ${escapeHtml(due)}</div><form class="submission-form stack-form" data-assignment-id="${item.id}" style="margin-top:12px"><label>My response<textarea name="response_text" maxlength="20000" rows="3" required placeholder="Write your answer here…">${escapeHtml(submission?.response_text || '')}</textarea></label><button class="button button-primary" type="submit">${submission ? 'Update submission' : 'Submit response'}</button>${submission ? `<small class="muted">Submitted ${escapeHtml(formatDateTime(submission.submitted_at))}</small>` : ''}</form></article>`;
    }
    // Staff payloads do not contain aggregate submission completion, so avoid an
    // inaccurate 'overdue' badge here. Student views still show per-student status.
    return `<article class="list-item"><span class="quick-icon lavender">▤</span><div class="list-content"><strong>${escapeHtml(item.title)}</strong><p>${escapeHtml(item.class_name)} · ${escapeHtml(item.subject)}</p><p>${escapeHtml(item.instructions || 'No instructions')} </p><p>Due: ${escapeHtml(due)} · By ${escapeHtml(item.created_by || 'Staff')}</p></div></article>`;
  }
  function renderNoticeItem(item, card = false) {
    if (card) return `<article class="notice-card"><div class="notice-meta"><span>${escapeHtml(item.class_name || 'Everyone')}</span><span>${escapeHtml(formatDateTime(item.published_at))}</span></div><h3>${escapeHtml(item.title)}</h3><p>${escapeHtml(item.body)}</p><div class="notice-footer">Published by ${escapeHtml(item.author || 'Staff')}</div></article>`;
    return `<article class="list-item"><span class="quick-icon mint">✦</span><div class="list-content"><strong>${escapeHtml(item.title)}</strong><p>${escapeHtml(item.class_name || 'Everyone')} · ${escapeHtml(formatDateTime(item.published_at))}</p><p>${escapeHtml(item.body)}</p></div></article>`;
  }
  function renderTodaySessions(items) {
    const container = $('#overviewSessions');
    container.innerHTML = items.length ? items.map(x => renderSessionItem(x, true)).join('') : '<div class="empty-state small-empty">No classes scheduled for this day. Your timetable is clear.</div>';
  }

  async function loadDashboard() {
    const data = await api('/api/v1/dashboard');
    state.user = data.user;
    state.institution = data.institution;
    state.sessions = data.sessions || [];
    state.assignments = data.assignments || [];
    state.notices = data.notices || [];
    applyRoleVisibility();
    renderStats(data.stats || {});
    renderTodaySessions(state.sessions);
    $('#overviewAssignments').innerHTML = state.assignments.length ? state.assignments.slice(0, 4).map(item => renderAssignmentItem(item, false)).join('') : '<div class="empty-state small-empty">No assignments yet.</div>';
    $('#overviewNotices').innerHTML = state.notices.length ? state.notices.slice(0, 4).map(item => renderNoticeItem(item, false)).join('') : '<div class="empty-state small-empty">No notices posted yet.</div>';
    $('#noticeCount').textContent = state.notices.length ? state.notices.length : '';
  }

  async function loadClassesAndUsers() {
    const data = await api('/api/v1/classes');
    state.classes = data.classes || [];
    populateSelect($('#sessionClass'), state.classes, 'Choose class');
    populateSelect($('#assignmentClass'), state.classes, 'Choose class');
    populateSelect($('#assessmentClass'), state.classes, 'Choose class');
    const noticeSelect = $('#noticeClass');
    const canPublishInstitutionNotice = state.user?.role === 'admin';
    populateSelect(noticeSelect, state.classes, canPublishInstitutionNotice ? 'Entire institution' : 'Choose class', canPublishInstitutionNotice);
    if (noticeSelect) noticeSelect.required = !canPublishInstitutionNotice;
    populateSelect($('#enrollClass'), state.classes, 'Choose class');
    populateSelect($('#studentImportClass'), state.classes, 'Choose class');
    populateSelect($('#subjectClass'), state.classes, 'Choose class');
    populateSelect($('#classTeacherClass'), state.classes, 'Choose class');
    // Select the first class for admin setup panels only; other forms stay explicit.
    for (const id of ['subjectClass', 'classTeacherClass']) {
      const select = $('#' + id);
      if (select && !select.value && state.classes.length) select.value = String(state.classes[0].id);
    }
    if (state.user?.role === 'admin') {
      const users = await api('/api/v1/users');
      state.users = users.users || [];
      const teachers = state.users.filter(u => u.role === 'teacher');
      const teacherOptions = teachers.map(u => ({ id: u.id, name: `${u.name} · ${u.email}` }));
      populateSelect($('#sessionTeacher'), teacherOptions, 'Unassigned');
      populateSelect($('#classTeacherUser'), teacherOptions, 'Choose teacher');
      const students = await api('/api/v1/students');
      state.students = students.students || [];
      populateSelect($('#enrollStudent'), state.students.map(u => ({ id: u.id, name: `${u.name} · ${u.student_code}` })), 'Choose student');
      // Populate subject suggestions and setup lists from the API-backed catalog.
      await Promise.all([
        loadClassSubjects($('#subjectClass')?.value, true),
        loadClassTeachers($('#classTeacherClass')?.value),
        loadClassSubjects($('#sessionClass')?.value, false),
        loadClassSubjects($('#assignmentClass')?.value, false)
      ]);
    } else {
      // Teachers can also use the subject suggestions for their assigned classes.
      await Promise.all([
        loadClassSubjects($('#sessionClass')?.value, false),
        loadClassSubjects($('#assignmentClass')?.value, false)
      ]);
    }
  }
  function populateSelect(element, items, placeholder, includeAll = false) {
    if (!element) return;
    const previous = element.value;
    const options = [];
    const firstValue = includeAll ? 'all' : '';
    options.push(`<option value="${firstValue}">${escapeHtml(placeholder)}</option>`);
    options.push(...items.map(item => `<option value="${item.id}">${escapeHtml(item.name)}</option>`));
    element.innerHTML = options.join('');
    if ([...element.options].some(option => option.value === previous)) element.value = previous;
  }

  async function loadClassSubjects(classId, renderManagement = false) {
    const list = $('#subjectList');
    if (!classId) {
      if (renderManagement && list) list.innerHTML = '<div class="empty-state small-empty">Create a class before adding subjects.</div>';
      return [];
    }
    const data = await api(`/api/v1/classes/${encodeURIComponent(classId)}/subjects`);
    const subjects = data.subjects || [];
    const datalistMarkup = subjects.map(subject => `<option value="${escapeHtml(subject.name)}"></option>`).join('');
    if ($('#sessionClass')?.value === String(classId) && $('#sessionSubjectOptions')) $('#sessionSubjectOptions').innerHTML = datalistMarkup;
    if ($('#assignmentClass')?.value === String(classId) && $('#assignmentSubjectOptions')) $('#assignmentSubjectOptions').innerHTML = datalistMarkup;
    if (renderManagement && list) {
      list.innerHTML = subjects.length ? subjects.map(subject => `
        <div class="list-item"><span class="quick-icon lavender">▤</span><div class="list-content"><strong>${escapeHtml(subject.name)}</strong><p>${escapeHtml(subject.class_name || '')}</p></div></div>`).join('')
        : '<div class="empty-state small-empty">No subjects yet. Add the first subject above.</div>';
    }
    return subjects;
  }

  async function loadClassTeachers(classId) {
    const list = $('#classTeacherList');
    if (!classId) {
      if (list) list.innerHTML = '<div class="empty-state small-empty">Create a class before assigning teachers.</div>';
      return;
    }
    const data = await api(`/api/v1/classes/${encodeURIComponent(classId)}/teachers`);
    const teachers = data.teachers || [];
    if (list) {
      list.innerHTML = teachers.length ? teachers.map(teacher => `
        <div class="list-item"><span class="avatar">${escapeHtml(asInitials(teacher.name))}</span><div class="list-content"><strong>${escapeHtml(teacher.name)}</strong><p>${escapeHtml(teacher.email)}</p></div></div>`).join('')
        : '<div class="empty-state small-empty">No teachers assigned yet.</div>';
    }
  }

  async function loadTimetable(date = $('#timetableDate')?.value || todayLocal()) {
    const input = $('#timetableDate');
    if (input && !input.value) input.value = todayLocal();
    const data = await api(`/api/v1/sessions?date=${encodeURIComponent(date)}`);
    state.sessions = data.sessions || [];
    $('#scheduleSubtitle').textContent = `${state.sessions.length} session${state.sessions.length === 1 ? '' : 's'} on ${formatDate(`${date}T12:00:00`)}`;
    $('#timetableList').innerHTML = state.sessions.length ? state.sessions.map(item => renderSessionItem(item, true)).join('') : '<div class="empty-state">No sessions on this date. Admins can schedule a class above.</div>';
    const availableForRegister = state.sessions.filter(item => item.status !== 'cancelled');
    populateSelect($('#attendanceSession'), availableForRegister.map(x => ({ id: x.id, name: `${formatTime(x.starts_at)} · ${x.subject} — ${x.class_name}` })), 'Select a session');
  }

  async function loadSessionsForAttendance() {
    const attendanceDate = $('#attendanceDate')?.value || todayLocal();
    const data = await api(`/api/v1/sessions?date=${encodeURIComponent(attendanceDate)}`);
    state.sessions = data.sessions || [];
    populateSelect($('#attendanceSession'), state.sessions.filter(x => x.status !== 'cancelled').map(x => ({ id: x.id, name: `${formatTime(x.starts_at)} · ${x.subject} — ${x.class_name}` })), 'Select a session');
    if (!state.sessions.length) $('#attendanceRoster').innerHTML = '<div class="empty-state">No class sessions on the selected date. Check your timetable.</div>';
  }

  async function openAttendance(sessionId) {
    if (!sessionId) { toast('Choose a class session first.', 'error'); return; }
    const data = await api(`/api/v1/sessions/${sessionId}/attendance`);
    state.attendanceSession = Number(sessionId);
    const rows = data.students || [];
    if (!rows.length) {
      $('#attendanceRoster').innerHTML = '<div class="empty-state">There are no enrolled students in this class yet. Enroll students from Classes & people.</div>';
      $('#attendanceActions').hidden = true;
      return;
    }
    $('#attendanceRoster').innerHTML = `<table class="data-table"><thead><tr><th>Student</th><th>Student code</th><th>Attendance status</th></tr></thead><tbody>${rows.map(student => `<tr data-student-id="${student.student_id}"><td><strong>${escapeHtml(student.name)}</strong></td><td>${escapeHtml(student.student_code)}</td><td><select class="attendance-status" aria-label="Attendance status for ${escapeHtml(student.name)}"><option value="">Choose status…</option>${['present','absent','late','excused'].map(status => `<option value="${status}" ${student.status === status ? 'selected' : ''}>${status[0].toUpperCase() + status.slice(1)}</option>`).join('')}</select></td></tr>`).join('')}</tbody></table><p class="status-note">Unselected rows will not be changed. Use “Excused” when appropriate under your institution's policy.</p>`;
    $('#attendanceActions').hidden = false;
  }

  async function loadMyAttendance() {
    const data = await api('/api/v1/attendance/mine');
    const rows = data.records || [];
    $('#myAttendanceList').innerHTML = rows.length ? `<table class="data-table"><thead><tr><th>Class / subject</th><th>Date</th><th>Status</th></tr></thead><tbody>${rows.map(row => `<tr><td><strong>${escapeHtml(row.subject)}</strong><br><span class="muted">${escapeHtml(row.class_name)}</span></td><td>${escapeHtml(formatDateTime(row.date))}</td><td><span class="status-tag ${escapeHtml(row.status)}">${escapeHtml(row.status)}</span></td></tr>`).join('')}</tbody></table>` : '<div class="empty-state">Your attendance history will appear here when a teacher records it.</div>';
  }

  async function loadAssignments() {
    const data = await api('/api/v1/assignments');
    state.assignments = data.assignments || [];
    $('#assignmentList').innerHTML = state.assignments.length ? (state.user?.role === 'student' ? `<div class="notice-grid">${state.assignments.map(item => renderAssignmentItem(item, true)).join('')}</div>` : state.assignments.map(item => renderAssignmentItem(item, false)).join('')) : '<div class="empty-state">No assignments are available yet.</div>';
    if (state.user?.role === 'student') {
      $$('.submission-form', $('#assignmentList')).forEach(form => form.addEventListener('submit', async event => {
        event.preventDefault();
        const id = form.dataset.assignmentId;
        const responseText = $('textarea[name="response_text"]', form).value.trim();
        try {
          await api(`/api/v1/assignments/${id}/submissions`, { method: 'POST', body: JSON.stringify({ response_text: responseText }) });
          toast('Your response has been saved.', 'success');
          await loadAssignments();
        } catch (error) { showError(error); }
      }));
    }
  }

  async function loadNotices() {
    const data = await api('/api/v1/notices');
    state.notices = data.notices || [];
    $('#noticeList').innerHTML = state.notices.length ? state.notices.map(item => renderNoticeItem(item, true)).join('') : '<div class="empty-state">No notices to show. Check back later for updates.</div>';
    $('#noticeCount').textContent = state.notices.length ? state.notices.length : '';
  }

  async function loadManagement() {
    await loadClassesAndUsers();
    $('#classList').innerHTML = state.classes.length ? state.classes.map(item => `<div class="list-item"><span class="quick-icon lavender">▦</span><div class="list-content"><strong>${escapeHtml(item.name)}</strong><p>${escapeHtml(item.kind)}${item.academic_year ? ` · ${escapeHtml(item.academic_year)}` : ''} · ${item.student_count} enrolled</p></div></div>`).join('') : '<div class="empty-state small-empty">Create your first class or batch.</div>';
  }

  async function loadFeedback() {
    // The API allows only institution admins to retrieve the feedback inbox.
    const data = await api('/api/v1/feedback');
    const items = data.feedback || [];
    const target = $('#feedbackList');
    if (!target) return;
    target.innerHTML = items.length ? items.map(item => `
      <article class="list-item feedback-record">
        <span class="quick-icon ${item.category === 'bug' ? 'peach' : item.category === 'idea' ? 'lavender' : 'mint'}">${item.category === 'bug' ? '!' : item.category === 'idea' ? '✧' : '♡'}</span>
        <div class="list-content"><strong>${escapeHtml(item.category)} · ${escapeHtml(item.reporter)}</strong>
          <p>${escapeHtml(item.message)}</p><p>${escapeHtml(item.page || 'General')} · ${escapeHtml(formatDateTime(item.created_at))} · ${escapeHtml(item.status)}</p></div>
      </article>`).join('') : '<div class="empty-state small-empty">No feedback has been submitted by this workspace yet.</div>';
  }

  async function loadReport() {
    const data = await api('/api/v1/reports/attendance');
    const counts = data.counts || {};
    const summary = `<div class="stats-grid" style="grid-template-columns:repeat(4,minmax(0,1fr));margin-bottom:12px">${Object.entries(counts).map(([name,value])=>`<div class="stat-card" style="min-height:90px"><span class="stat-label">${escapeHtml(name)}</span><strong>${escapeHtml(value)}</strong></div>`).join('')}</div>`;
    const table = (data.records || []).length ? `<table class="data-table"><thead><tr><th>Student</th><th>Class</th><th>Session</th><th>Status</th></tr></thead><tbody>${data.records.map(row=>`<tr><td>${escapeHtml(row.student)}<br><span class="muted">${escapeHtml(row.student_code)}</span></td><td>${escapeHtml(row.class_name)}</td><td>${escapeHtml(row.subject)}<br><span class="muted">${escapeHtml(formatDateTime(row.starts_at))}</span></td><td><span class="status-tag ${escapeHtml(row.status)}">${escapeHtml(row.status)}</span></td></tr>`).join('')}</tbody></table>` : '<div class="empty-state small-empty">No attendance records match yet.</div>';
    $('#attendanceReport').innerHTML = summary + table;
  }

  function normalizeHeader(value) {
    return String(value ?? '').replace(/^\uFEFF/, '').trim().toLowerCase().replace(/[\s._-]+/g, '');
  }

  function parseCsvText(text) {
    // Small RFC-4180-style CSV reader used when the optional workbook library is unavailable.
    const rows = [];
    let row = [], field = '', quoted = false;
    for (let i = 0; i < text.length; i += 1) {
      const ch = text[i];
      if (ch === '"') {
        if (quoted && text[i + 1] === '"') { field += '"'; i += 1; }
        else quoted = !quoted;
      } else if (ch === ',' && !quoted) {
        row.push(field); field = '';
      } else if ((ch === '\n' || ch === '\r') && !quoted) {
        if (ch === '\r' && text[i + 1] === '\n') i += 1;
        row.push(field); field = '';
        if (row.some(cell => String(cell).trim() !== '')) rows.push(row);
        row = [];
      } else field += ch;
    }
    row.push(field);
    if (row.some(cell => String(cell).trim() !== '')) rows.push(row);
    if (quoted) throw new Error('The CSV file has an unclosed quote. Check the file and try again.');
    if (rows.length < 2) throw new Error('The CSV file needs a header row and at least one student.');
    const headers = rows[0].map(header => String(header).trim());
    return rows.slice(1).map(cells => Object.fromEntries(headers.map((header, index) => [header, cells[index] ?? ''])));
  }

  async function readStudentSpreadsheet(file) {
    const extension = (file.name.split('.').pop() || '').toLowerCase();
    if (!['csv', 'xlsx', 'xls'].includes(extension)) {
      throw new Error('Choose a .csv, .xlsx or .xls file.');
    }

    let sourceRows;
    if (window.XLSX) {
      // SheetJS reads both Excel workbooks and CSV while keeping parsing in the browser.
      const workbook = window.XLSX.read(await file.arrayBuffer(), { type: 'array' });
      if (!workbook.SheetNames.length) throw new Error('The spreadsheet has no worksheet.');
      sourceRows = window.XLSX.utils.sheet_to_json(workbook.Sheets[workbook.SheetNames[0]], { defval: '', raw: false });
    } else if (extension === 'csv') {
      sourceRows = parseCsvText(await file.text());
    } else {
      throw new Error('Excel support did not load. Check your internet connection or save the sheet as CSV and try again.');
    }
    if (!sourceRows.length) throw new Error('The spreadsheet is empty.');
    if (sourceRows.length > 300) throw new Error('Import at most 300 students per batch. Split the spreadsheet and retry.');

    const first = sourceRows[0] || {};
    const normalizedHeaders = Object.keys(first).map(normalizeHeader);
    const hasName = normalizedHeaders.some(key => ['name', 'studentname', 'fullname', 'student'].includes(key));
    const hasEmail = normalizedHeaders.some(key => ['email', 'emailaddress', 'emailid'].includes(key));
    if (!hasName || !hasEmail) {
      throw new Error('Use column headers Name and Email. Student Code (or Roll No) is optional.');
    }

    const findValue = (row, aliases) => {
      const wanted = aliases.map(normalizeHeader);
      const key = Object.keys(row).find(header => wanted.includes(normalizeHeader(header)));
      return key ? String(row[key] ?? '').trim() : '';
    };
    return sourceRows.map(row => ({
      name: findValue(row, ['Name', 'Student Name', 'Full Name', 'Student']),
      email: findValue(row, ['Email', 'Email Address', 'Email ID']).toLowerCase(),
      student_code: findValue(row, ['Student Code', 'Roll No', 'Roll Number', 'RollNo', 'Enrollment No', 'Enrollment Number', 'Admission Number'])
    })).filter(row => row.name || row.email || row.student_code);
  }

  function renderStudentImportPreview(rows) {
    pendingStudentImportRows = rows;
    const target = $('#studentImportPreview');
    const previewRows = rows.slice(0, 8);
    target.hidden = false;
    target.innerHTML = `
      <div class="row-between wrap"><div><h3>Review import</h3><p class="muted">${rows.length} row${rows.length === 1 ? '' : 's'} ready to send for validation. Only the first 8 are shown below.</p></div><span class="soft-tag">Preview</span></div>
      <div class="table-wrap"><table class="data-table"><thead><tr><th>Name</th><th>Email</th><th>Student code</th></tr></thead><tbody>
      ${previewRows.map(row => `<tr><td>${escapeHtml(row.name || '—')}</td><td>${escapeHtml(row.email || '—')}</td><td>${escapeHtml(row.student_code || 'Auto-generate')}</td></tr>`).join('')}
      </tbody></table></div>
      <p class="import-warning" style="margin-top:12px">Each imported student account receives a randomly generated temporary password. Download the credentials once and share them securely. Password-reset emails are not part of this MVP.</p>
      <div class="row wrap" style="justify-content:flex-end;margin-top:12px"><button type="button" class="button button-soft" id="cancelStudentImport">Cancel</button><button type="button" class="button button-primary" id="confirmStudentImport">Import ${rows.length} students</button></div>`;
  }

  async function confirmStudentImport() {
    const button = $('#confirmStudentImport');
    const classId = $('#studentImportClass')?.value;
    if (!classId) { toast('Choose a class or batch first.', 'error'); return; }
    if (!pendingStudentImportRows.length) { toast('Preview a spreadsheet before importing.', 'error'); return; }
    if (button) { button.disabled = true; button.textContent = 'Importing…'; }
    try {
      const result = await api(`/api/v1/classes/${encodeURIComponent(classId)}/students/import`, {
        method: 'POST', body: JSON.stringify({ students: pendingStudentImportRows })
      });
      lastImportCredentials = result.credentials || [];
      const resultTarget = $('#studentImportResult');
      resultTarget.hidden = false;
      resultTarget.innerHTML = `
        <h3>Import result</h3>
        <p class="import-success">Imported <strong>${escapeHtml(result.imported_count ?? 0)}</strong> student${result.imported_count === 1 ? '' : 's'} into <strong>${escapeHtml(result.class_name || 'the selected class')}</strong>. Skipped: <strong>${escapeHtml(result.skipped_count ?? 0)}</strong>.</p>
        ${lastImportCredentials.length ? '<p>Temporary passwords are returned only once and are not stored as plain text. Download this credential file now and distribute it privately.</p><button type="button" class="button button-primary" id="downloadImportCredentials">Download temporary credentials (CSV)</button>' : '<p>No new credentials were generated. Review the skipped rows below.</p>'}
        ${(result.skipped || []).length ? `<details style="margin-top:12px"><summary>Why rows were skipped</summary><ul class="import-error-list">${result.skipped.map(item => `<li>Row ${escapeHtml(item.row)}: ${escapeHtml(item.reason)}</li>`).join('')}</ul></details>` : ''}`;
      pendingStudentImportRows = [];
      $('#studentImportPreview').hidden = true;
      $('#studentImportPreview').innerHTML = '';
      $('#studentImportForm').reset();
      toast(`Import complete: ${result.imported_count} created, ${result.skipped_count} skipped.`, 'success');
      // Saving succeeded above; a later list refresh failure must not imply the import rolled back.
      try { await loadManagement(); }
      catch (_) { toast('Import saved. Refresh the class list when your connection is stable.', 'error'); }
    } catch (error) {
      showError(error);
      if (button) { button.disabled = false; button.textContent = 'Try import again'; }
    }
  }

  function downloadTemporaryCredentials() {
    if (!lastImportCredentials.length) return;
    const columns = [
      ['Name', 'name'], ['Email', 'email'], ['Student Code', 'student_code'], ['Temporary Password', 'temporary_password']
    ];
    const quoteCsv = value => `"${String(value ?? '').replace(/"/g, '""')}"`;
    const csv = [columns.map(([label]) => quoteCsv(label)).join(','), ...lastImportCredentials.map(row => columns.map(([, key]) => quoteCsv(row[key])).join(','))].join('\r\n');
    const blob = new Blob(['\ufeff', csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `nextgenpathashala-student-credentials-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1500);
    // Keep the one-time response in memory in case the browser's download UI needs a retry.
    const button = $('#downloadImportCredentials');
    if (button) button.textContent = 'Download again (credentials are sensitive)';
    toast('Credential file downloaded. Store and share it securely.', 'success');
  }

  function bindForm(id, callback) {
    const form = $('#' + id);
    if (form) form.addEventListener('submit', async event => {
      event.preventDefault();
      const button = $('button[type="submit"]', form);
      const previousText = button?.textContent;
      if (button) { button.disabled = true; button.textContent = 'Saving…'; }
      try { await callback(form); }
      catch (error) { showError(error); }
      finally { if (button) { button.disabled = false; button.textContent = previousText; } }
    });
  }

  const STUDY_QUESTIONS = [
    {id:'py1',topic:'python',q:'What is the main purpose of a Python function?',options:['To group reusable instructions','To store only numbers','To install packages','To create a database automatically'],answer:0,why:'A function packages instructions under a name so they can be reused and tested.'},
    {id:'py2',topic:'python',q:'What is the difference between return and print?',options:['They are identical','return sends a value back; print displays text','print returns every value to the caller','return only works with strings'],answer:1,why:'return gives a result to the caller; print writes output to the console.'},
    {id:'py3',topic:'python',q:'Which Python structure stores key-value pairs?',options:['tuple','set','dictionary','string'],answer:2,why:'A dictionary maps unique keys to values, for example {"name": "Asha"}.'},
    {id:'ml1',topic:'ml',q:'Why do we keep a test set separate from training data?',options:['To increase training rows','To estimate performance on unseen data','To remove all labels','To guarantee 100% accuracy'],answer:1,why:'A separate test set estimates how well a model generalizes to unseen examples.'},
    {id:'ml2',topic:'ml',q:'Which metric is especially useful when false negatives are costly?',options:['Recall','Training time','File size','Number of features'],answer:0,why:'Recall measures the proportion of actual positives correctly found: TP/(TP+FN).'},
    {id:'ml3',topic:'ml',q:'What is overfitting?',options:['Model performs well on new data only','Model memorizes training patterns and generalizes poorly','Model has no parameters','Dataset has no missing values'],answer:1,why:'An overfit model learns noise or specifics of training data and performs worse on unseen data.'},
    {id:'nlp1',topic:'nlp',q:'What does TF-IDF help estimate?',options:['Importance of a term in a document relative to a corpus','The number of neural network layers','Image resolution','CPU temperature'],answer:0,why:'TF-IDF combines term frequency with inverse document frequency to down-weight common terms.'},
    {id:'nlp2',topic:'nlp',q:'In Word2Vec CBOW, the model predicts…',options:['Context words from a target word','A target word from surrounding context','The document language only','The number of sentences'],answer:1,why:'CBOW uses surrounding context words to predict the center/target word.'},
    {id:'nlp3',topic:'nlp',q:'Which task assigns labels such as noun and verb to tokens?',options:['POS tagging','Image segmentation','Regression','Clustering pixels'],answer:0,why:'Part-of-speech tagging labels tokens with grammatical categories such as noun, verb or adjective.'},
    {id:'st1',topic:'stats',q:'What does a p-value represent under the null hypothesis?',options:['Probability the null is definitely true','Probability of results at least this extreme, assuming the null','The sample mean','The effect size automatically'],answer:1,why:'A p-value is computed assuming the null hypothesis; it is not the probability that the null is true.'},
    {id:'st2',topic:'stats',q:'Which test commonly compares means of two independent groups when assumptions are suitable?',options:['Independent-samples t-test','Chi-square goodness of fit only','Pearson correlation only','K-means'],answer:0,why:'An independent-samples t-test compares group means when its assumptions are reasonably met.'},
    {id:'st3',topic:'stats',q:'What is the mean of 2, 4 and 9?',options:['4','5','6','15'],answer:1,why:'Mean = (2 + 4 + 9) / 3 = 15 / 3 = 5.'},
    {id:'py4',topic:'python',q:'Which keyword handles a possible exception?',options:['catch','try/except','error','final'],answer:1,why:'A try block contains code that may fail; except handles a matching exception.'},
    {id:'py5',topic:'python',q:'Which expression creates a list with three items?',options:['[1, 2, 3]','(1)','{1: 2, 3}','list = 3'],answer:0,why:'Square brackets create a Python list. Parentheses normally create a tuple when separated by commas.'},
    {id:'ml4',topic:'ml',q:'Precision is calculated as…',options:['TP/(TP+FP)','TP/(TP+FN)','TN/(TN+FP)','(TP+TN)/all'],answer:0,why:'Precision is the proportion of positive predictions that are correct: TP divided by TP plus FP.'},
    {id:'ml5',topic:'ml',q:'What is a validation set commonly used for?',options:['Final unbiased evaluation only','Choosing hyperparameters during development','Replacing all training data','Guaranteeing zero error'],answer:1,why:'Validation data helps select models and tune hyperparameters; the test set is held back for final evaluation.'},
    {id:'nlp4',topic:'nlp',q:'What is stopword removal?',options:['Removing common words that may add little task-specific value','Translating every word','Sorting words alphabetically','Converting text to images'],answer:0,why:'Stopword removal filters frequent terms such as “the” or “and” when they do not help the task.'},
    {id:'nlp5',topic:'nlp',q:'How does lemmatization differ from basic stemming?',options:['It always removes punctuation only','It aims to return a dictionary base form using linguistic information','It turns all words into numbers','It detects images'],answer:1,why:'Lemmatization uses vocabulary and linguistic context to map forms to lemmas; stemming often uses simpler trimming rules.'},
    {id:'st4',topic:'stats',q:'What is the median of 2, 4, 9?',options:['2','4','5','9'],answer:1,why:'The median is the middle value after sorting. In 2, 4, 9, it is 4.'},
    {id:'st5',topic:'stats',q:'A Type I error occurs when we…',options:['Fail to reject a false null hypothesis','Reject a true null hypothesis','Calculate a mean correctly','Increase sample size'],answer:1,why:'A Type I error is a false positive: rejecting the null hypothesis when it is actually true.'},
    {id:'ma1',topic:'maths',q:'What is 15% of 200?',options:['15','20','30','45'],answer:2,why:'15% of 200 = 0.15 × 200 = 30.'},
    {id:'ma2',topic:'maths',q:'Solve 3x = 21.',options:['6','7','8','18'],answer:1,why:'Divide both sides by 3: x = 21/3 = 7.'},
    {id:'ma3',topic:'maths',q:'What is the area of a rectangle 8 cm by 3 cm?',options:['11 cm²','16 cm²','24 cm²','22 cm²'],answer:2,why:'Area = length × width = 8 × 3 = 24 cm².'},
    {id:'ma4',topic:'maths',q:'What is the square root of 144?',options:['10','11','12','14'],answer:2,why:'12 × 12 = 144, so √144 = 12.'},
    {id:'ma5',topic:'maths',q:'What is 1/4 + 1/4?',options:['1/8','1/2','2/8','1/4'],answer:1,why:'The denominators match, so add the numerators: 1/4 + 1/4 = 2/4 = 1/2.'},
    {id:'sc1',topic:'science',q:'Which gas do plants absorb for photosynthesis?',options:['Oxygen','Carbon dioxide','Hydrogen','Helium'],answer:1,why:'Plants take in carbon dioxide and use light energy and water to make sugars during photosynthesis.'},
    {id:'sc2',topic:'science',q:'What is the SI unit of force?',options:['Joule','Watt','Newton','Pascal'],answer:2,why:'Force is measured in newtons (N). One newton is one kilogram metre per second squared.'},
    {id:'sc3',topic:'science',q:'Which part of a typical human cell contains most genetic material?',options:['Cell membrane','Nucleus','Cytoplasm only','Ribosome'],answer:1,why:'The nucleus contains most of the cell’s DNA in typical human cells.'},
    {id:'sc4',topic:'science',q:'At standard atmospheric pressure, water freezes at…',options:['0°C','10°C','32°C','100°C'],answer:0,why:'Pure water freezes at 0°C (32°F) under standard atmospheric pressure.'},
    {id:'sc5',topic:'science',q:'Which is a renewable energy source?',options:['Coal','Petroleum','Solar energy','Natural gas'],answer:2,why:'Solar energy is replenished by sunlight, unlike fossil fuels.'},
    {id:'en1',topic:'english',q:'Choose the grammatically correct sentence.',options:['She go to class daily.','She goes to class daily.','She going class daily.','She gone to class daily.'],answer:1,why:'With third-person singular “she” in the simple present, the verb is “goes”.'},
    {id:'en2',topic:'english',q:'Which word is closest in meaning to “concise”?',options:['Brief','Confusing','Noisy','Late'],answer:0,why:'Concise means brief but still giving the necessary information.'},
    {id:'en3',topic:'english',q:'What is the main purpose of a topic sentence?',options:['To introduce the paragraph’s main idea','To list references only','To end every essay','To correct spelling only'],answer:0,why:'A topic sentence introduces the central point developed in the paragraph.'},
    {id:'en4',topic:'english',q:'Which is a noun in the sentence “The careful student wrote notes”?',options:['careful','wrote','student','notes quickly'],answer:2,why:'“Student” names a person and is a noun. “Careful” is an adjective and “wrote” is a verb.'},
    {id:'en5',topic:'english',q:'Choose the correct plural of “analysis”.',options:['analysises','analysies','analyses','analysis'],answer:2,why:'The plural form of analysis is analyses.'},
    {id:'co1',topic:'commerce',q:'The basic accounting equation is…',options:['Assets = Liabilities + Equity','Assets = Income − Expenses','Profit = Assets + Liabilities','Cash = Sales × Tax'],answer:0,why:'The accounting equation states assets equal liabilities plus owners’ equity.'},
    {id:'co2',topic:'commerce',q:'A budget is mainly used to…',options:['Plan expected income and spending','Record only employee names','Guarantee profit','Replace all invoices'],answer:0,why:'A budget estimates income and expenditure to support planning and control.'},
    {id:'co3',topic:'commerce',q:'If revenue is ₹1,000 and total cost is ₹700, profit is…',options:['₹300','₹700','₹1,000','₹1,700'],answer:0,why:'Profit = revenue − cost = ₹1,000 − ₹700 = ₹300.'},
    {id:'co4',topic:'commerce',q:'Which is generally an asset for a business?',options:['Bank balance','Loan payable','Wages payable','Accounts payable'],answer:0,why:'Cash or a bank balance is an asset; amounts owed are liabilities.'},
    {id:'co5',topic:'commerce',q:'What does cash flow track?',options:['Only accounting profit','Cash entering and leaving a business','Only customer names','Stock market prices exclusively'],answer:1,why:'Cash-flow tracking records cash inflows and outflows over a period.'}
  ];
  let activeStudyQuiz = null;
  function studyHistoryKey() { return `ngp_study_scores_${state.user?.id || 'guest'}`; }
  function studyHistory() { try { const h=JSON.parse(localStorage.getItem(studyHistoryKey())||'[]'); return Array.isArray(h)?h:[]; } catch (_) { return []; } }
  function renderStudyHistory() {
    const el=$('#studyScoreHistory'); if(!el) return;
    const history=studyHistory().slice(0,5);
    el.innerHTML=history.length?history.map(x=>`<div class="list-item"><div class="list-content"><strong>${escapeHtml(x.label)}</strong><p>${escapeHtml(x.score)}/${escapeHtml(x.total)} · ${escapeHtml(x.date)}</p></div></div>`).join(''):'<p class="muted tiny">No scores yet. Complete a practice set or mock test to start tracking on this device.</p>';
  }
  async function beginStudyQuiz(kind) {
    if (kind === 'practice') {
      const materialIds = $$('#practiceNoteOptions input[type="checkbox"]:checked').map(input => input.value);
      const button = $('#startPractice');
      const target = $('#practiceArea');
      if (!materialIds.length || !button || !target) return;
      button.disabled = true;
      button.textContent = 'Generating…';
      target.textContent = 'Generating questions from the selected notes…';
      try {
        const result = await api('/api/v1/study-materials/practice-quiz', {
          method: 'POST', body: JSON.stringify({ material_ids: materialIds })
        });
        activeStudyQuiz = { kind, label: result.label, questions: result.questions, answers: {} };
        renderStudyQuiz();
        $('#practiceNotesPicker').open = false;
      } catch (error) {
        target.textContent = error.message;
      } finally {
        button.disabled = !$$('#practiceNoteOptions input[type="checkbox"]:checked').length;
        button.textContent = 'Generate five questions';
      }
      return;
    }
    let pool=[...STUDY_QUESTIONS];
    pool=pool.sort(()=>Math.random()-.5);
    const count=10;
    activeStudyQuiz={kind,label:'Mock test',questions:pool.slice(0,count),answers:{}};
    renderStudyQuiz();
  }
  function renderStudyQuiz() {
    const quiz=activeStudyQuiz; if(!quiz)return;
    const target=$(quiz.kind==='mock'?'#mockTestArea':'#practiceArea'); if(!target)return;
    target.innerHTML=`<form class="study-quiz-form"><p class="muted tiny">${quiz.questions.length} questions · Select one answer per question.</p>${quiz.questions.map((q,i)=>`<fieldset class="study-question"><legend>${i+1}. ${escapeHtml(q.q)}</legend>${q.options.map((o,j)=>`<label class="study-option"><input type="radio" name="${q.id}" value="${j}" ${quiz.answers[q.id]===j?'checked':''} required><span>${escapeHtml(o)}</span></label>`).join('')}<div class="study-explanation" id="why-${q.id}" hidden></div></fieldset>`).join('')}<button class="button button-primary" type="submit">Submit answers</button></form>`;
    $('.study-quiz-form',target)?.addEventListener('submit',e=>{e.preventDefault();let score=0;quiz.questions.forEach(q=>{const chosen=Number(new FormData(e.currentTarget).get(q.id));quiz.answers[q.id]=chosen;if(chosen===q.answer)score++;const why=$(`#why-${q.id}`,target);why.hidden=false;why.innerHTML=`<strong>${chosen===q.answer?'Correct':'Review this answer'}.</strong> ${escapeHtml(q.why)} <span>Correct answer: ${escapeHtml(q.options[q.answer])}</span>`;});const old=$('.study-result',target);old?.remove();const result=document.createElement('div');result.className='study-result';result.setAttribute('role','status');result.innerHTML=`<h3>Score: ${score}/${quiz.questions.length} (${Math.round(score/quiz.questions.length*100)}%)</h3><p>${score===quiz.questions.length?'Excellent work!':score>=Math.ceil(quiz.questions.length*.6)?'Good progress. Review the explanations below.':'Keep practising. Read each explanation and try again.'}</p>`;target.prepend(result);try{const h=studyHistory();h.unshift({label:quiz.label,score,total:quiz.questions.length,date:new Date().toLocaleDateString()});localStorage.setItem(studyHistoryKey(),JSON.stringify(h.slice(0,20)));}catch(_){}renderStudyHistory();const submit=$('button[type="submit"]',target);if(submit){submit.disabled=true;submit.textContent='Submitted';}});
  }
  function tutorReply(question) {
    const q=question.toLowerCase();
    const answers=[
      {keys:['precision','recall','f1'],text:'Precision = TP/(TP+FP): of the items predicted positive, how many were correct. Recall = TP/(TP+FN): of all actual positives, how many were found. Example: for disease screening, high recall helps miss fewer real cases. F1 is the harmonic mean of precision and recall.'},
      {keys:['overfit','overfitting','underfit','underfitting'],text:'Overfitting means a model learns training-specific noise and performs poorly on unseen data. Try more representative data, regularization, simpler models, cross-validation or early stopping. Underfitting means the model is too simple to capture the pattern.'},
      {keys:['tf-idf','tfidf','bag of words','bow'],text:'Bag of Words represents text using token counts and ignores word order. TF-IDF weights a term by its frequency in one document and how rare it is across documents, so common corpus-wide words get lower weight.'},
      {keys:['cbow','skip-gram','word2vec','embedding'],text:'Word2Vec learns dense word vectors. CBOW predicts a target word from its surrounding context; Skip-gram predicts context words from a target word. A memory trick: CBOW = context brings target; Skip-gram = target skips out to context.'},
      {keys:['p-value','p value','hypothesis','null hypothesis'],text:'A p-value is the probability, assuming the null hypothesis is true, of observing results at least as extreme as those seen. If p is below a prechosen alpha such as 0.05, reject the null under that decision rule. It is not the probability that the null is true.'},
      {keys:['python','return','print','function'],text:'In Python, a function is defined with def. print() displays information, while return sends a value back to the caller. Example: def square(x): return x*x. Then square(4) evaluates to 16.'},
      {keys:['study plan','exam','revision','prepare','memorize'],text:'Try a 25-minute cycle: 5 minutes recall definitions without notes, 10 minutes solve MCQs, 5 minutes explain mistakes in your own words, and 5 minutes revisit weak concepts. Repeat after a break and practise spaced retrieval tomorrow.'},
      {keys:['mock test','practice','quiz','mcq'],text:'Open Practice MCQs to practise five topic-focused questions, or start the 10-question mock test. Submit once to see your score and explanations. Scores are stored only in this browser on this device.'},
      {keys:['machine learning','supervised','unsupervised'],text:'Supervised learning learns from labelled examples (such as spam/not spam). Unsupervised learning looks for structure in unlabelled data (such as customer clusters). Reinforcement learning learns actions through rewards and penalties.'},
      {keys:['nlp','tokenization','stemming','lemmatization'],text:'NLP works with human language. Tokenization splits text into units; stemming crudely trims word endings; lemmatization maps a word to its dictionary base form using linguistic information. Example: “running” may lemmatize to “run”.'}
    ];
    const match=answers.find(a=>a.keys.some(k=>q.includes(k)));
    return match?match.text:'I can help you break this down, but my built-in knowledge is limited. Tell me the subject and exact concept, or ask for a definition, worked example, formula, memory trick or practice MCQ. For syllabus-specific answers, compare with your teacher’s notes.';
  }
  function addChatMessage(who,text) {
    const log=$('#studyChatLog');if(!log)return;
    const bubble=document.createElement('div');bubble.className=`study-message ${who}`;
    const strong=document.createElement('strong');strong.textContent=who==='student'?'You':'Study Buddy';
    const p=document.createElement('p');p.textContent=text;
    bubble.append(strong,p);log.append(bubble);log.scrollTop=log.scrollHeight;
  }
  function updatePracticeNoteSelection() {
    const selectedCount = $$('#practiceNoteOptions input[type="checkbox"]:checked').length;
    const summary = $('#practiceNotesSummary');
    const button = $('#startPractice');
    if (summary) summary.textContent = selectedCount ? `${selectedCount} note${selectedCount === 1 ? '' : 's'} selected` : 'Choose course notes';
    if (button) button.disabled = selectedCount === 0;
  }
  function renderPracticeNoteOptions(materials) {
    const options = $('#practiceNoteOptions');
    if (!options) return;
    options.replaceChildren();
    if (!materials.length) {
      const empty = document.createElement('p'); empty.className = 'muted tiny'; empty.textContent = 'Upload notes in Study Buddy to practise from them.'; options.append(empty);
      updatePracticeNoteSelection();
      return;
    }
    materials.forEach(material => {
      const label = document.createElement('label'); label.className = 'practice-note-option';
      const checkbox = document.createElement('input'); checkbox.type = 'checkbox'; checkbox.value = material.id;
      const name = document.createElement('span'); name.textContent = material.name;
      label.append(checkbox, name); options.append(label);
    });
    updatePracticeNoteSelection();
  }
  async function loadStudyMaterials() {
    const list = $('#studyMaterialList'); if (!list) return;
    try {
      const result = await api('/api/v1/study-materials');
      list.replaceChildren();
      renderPracticeNoteOptions(result.materials || []);
      if (!result.materials?.length) {
        const empty = document.createElement('p'); empty.className = 'muted tiny'; empty.textContent = 'No course notes uploaded yet.'; list.append(empty); return;
      }
      result.materials.forEach(material => {
        const row = document.createElement('div'); row.className = 'list-item';
        const label = document.createElement('span'); label.textContent = `${material.name} · ${material.chars.toLocaleString()} characters`;
        const remove = document.createElement('button'); remove.type = 'button'; remove.className = 'button button-soft'; remove.textContent = 'Remove';
        remove.addEventListener('click', async () => { try { await api(`/api/v1/study-materials/${encodeURIComponent(material.id)}`, {method:'DELETE'}); toast('Course notes removed.', 'success'); await loadStudyMaterials(); } catch (err) { showError(err); } });
        row.append(label, remove); list.append(row);
      });
    } catch (err) {
      list.textContent = err.message;
      const options = $('#practiceNoteOptions');
      if (options) options.textContent = err.message;
      updatePracticeNoteSelection();
    }
  }

  let assessmentDrafts = [];
  function renderAssessmentDrafts() {
    const list = $('#assessmentDraftList');
    if (!list) return;
    $('#assessmentDraftCount').textContent = `${assessmentDrafts.length} question${assessmentDrafts.length === 1 ? '' : 's'} added`;
    list.innerHTML = assessmentDrafts.length ? assessmentDrafts.map((q, index) =>
      `<div class="list-item"><div class="list-content"><strong>${index + 1}. ${escapeHtml(q.prompt)}</strong><p>Correct answer: ${escapeHtml(q.options[q.correct_index])}</p></div><button class="button button-soft" type="button" data-remove-assessment-question="${index}" aria-label="Remove question ${index + 1}">Remove</button></div>`
    ).join('') : '<p class="muted tiny">Add one or more questions, then publish the test to the selected class.</p>';
  }
  function addAssessmentDraft() {
    const prompt = $('#assessmentQuestionPrompt')?.value.trim() || '';
    const options = [0, 1, 2, 3].map(i => $(`#assessmentOption${i}`)?.value.trim() || '');
    if (!prompt) { toast('Enter a question first.', 'error'); return; }
    if (options.some(option => !option)) { toast('Fill all four answer options.', 'error'); return; }
    if (assessmentDrafts.length >= 50) { toast('An assessment can contain at most 50 questions.', 'error'); return; }
    assessmentDrafts.push({prompt, options, correct_index:Number($('#assessmentCorrectIndex')?.value || 0), explanation:$('#assessmentExplanation')?.value.trim() || ''});
    $('#assessmentQuestionPrompt').value = '';
    [0, 1, 2, 3].forEach(i => { $(`#assessmentOption${i}`).value = ''; });
    $('#assessmentCorrectIndex').value = '0';
    $('#assessmentExplanation').value = '';
    renderAssessmentDrafts();
  }
  async function loadAssessments() {
    const target = $('#assessmentList');
    if (!target) return;
    if (isStaff()) populateSelect($('#assessmentClass'), state.classes, 'Choose class');
    try {
      const data = await api('/api/v1/assessments');
      const items = data.assessments || [];
      target.innerHTML = items.length ? items.map(item => isStaff()
        ? `<article class="list-item"><span class="quick-icon lavender">✓</span><div class="list-content"><strong>${escapeHtml(item.title)}</strong><p>${escapeHtml(item.class_name)} · ${item.question_count} questions · ${item.attempt_count || 0} submitted</p><p>${item.due_at ? `Deadline ${escapeHtml(formatDateTime(item.due_at))}` : 'No deadline'}</p></div><button class="button button-soft" type="button" data-assessment-results="${item.id}">View results</button><button class="button button-soft" type="button" data-assessment-open="${item.id}">Preview</button></article>`
        : `<article class="list-item"><span class="quick-icon mint">✓</span><div class="list-content"><strong>${escapeHtml(item.title)}</strong><p>${escapeHtml(item.class_name)} · ${item.question_count} questions</p><p>${item.attempted ? `Submitted · score ${item.result?.score ?? 0}/${item.result?.total ?? item.question_count}` : item.deadline_passed ? 'Deadline passed' : item.due_at ? `Deadline ${escapeHtml(formatDateTime(item.due_at))}` : 'Ready to take'}</p></div><button class="button button-primary" type="button" data-assessment-open="${item.id}" ${item.deadline_passed && !item.attempted ? 'disabled' : ''}>${item.attempted ? 'Review result' : item.deadline_passed ? 'Closed' : 'Start test'}</button></article>`
      ).join('') : '<div class="empty-state small-empty">No classroom assessments yet.</div>';
    } catch (error) { target.textContent = error.message; }
  }
  function renderAssessmentReview(results, score, total) {
    const target = $('#assessmentRunner');
    if (!target) return;
    target.innerHTML = `<section class="assessment-result"><h3>Result: ${escapeHtml(score)}/${escapeHtml(total)} (${total ? Math.round(score / total * 100) : 0}%)</h3>${results.map((q, i) => `<article class="study-question"><strong>${i + 1}. ${escapeHtml(q.prompt)}</strong><p class="${q.correct ? 'assessment-correct' : 'assessment-incorrect'}">${q.correct ? 'Correct' : `Incorrect · correct answer: ${escapeHtml(q.options[q.correct_index])}`}</p>${q.explanation ? `<p>${escapeHtml(q.explanation)}</p>` : ''}</article>`).join('')}</section>`;
    target.scrollIntoView({behavior:'smooth', block:'start'});
  }
  async function openAssessment(id) {
    const target = $('#assessmentRunner');
    if (!target) return;
    target.textContent = 'Loading assessment…';
    try {
      const data = await api(`/api/v1/assessments/${encodeURIComponent(id)}`);
      const assessment = data.assessment;
      if (data.attempt) {
        renderAssessmentReview(data.attempt.results, data.attempt.score, data.attempt.total);
        return;
      }
      if (isStaff()) {
        target.innerHTML = `<section class="assessment-result"><h3>${escapeHtml(assessment.title)} — answer-key preview</h3><p>${escapeHtml(assessment.instructions || '')}</p>${data.questions.map((q, i) => `<article class="study-question"><strong>${i + 1}. ${escapeHtml(q.prompt)}</strong><p>Correct: ${escapeHtml(q.options[q.correct_index])}</p><p>${escapeHtml(q.explanation || '')}</p></article>`).join('')}</section>`;
        return;
      }
      target.innerHTML = `<section class="assessment-runner-card"><h3>${escapeHtml(assessment.title)}</h3><p>${escapeHtml(assessment.instructions || 'Answer the questions and submit once.')}</p>${assessment.due_at ? `<p class="tiny muted">Deadline: ${escapeHtml(formatDateTime(assessment.due_at))}</p>` : ''}<form id="assessmentAttemptForm" class="stack-form">${data.questions.map((q, i) => `<fieldset class="study-question"><legend>${i + 1}. ${escapeHtml(q.prompt)}</legend>${q.options.map((option, optionIndex) => `<label class="study-option"><input type="radio" name="q${i}" value="${optionIndex}" required><span>${escapeHtml(option)}</span></label>`).join('')}</fieldset>`).join('')}<button class="button button-primary" type="submit">Submit assessment</button></form></section>`;
      $('#assessmentAttemptForm')?.addEventListener('submit', async event => {
        event.preventDefault();
        const form = event.currentTarget;
        const button = $('button[type="submit"]', form);
        button.disabled = true; button.textContent = 'Submitting…';
        const formData = new FormData(form);
        const answers = data.questions.map((_, i) => { const value = formData.get(`q${i}`); return value === null ? null : Number(value); });
        try {
          const result = await api(`/api/v1/assessments/${encodeURIComponent(id)}/attempts`, {method:'POST', body:JSON.stringify({answers})});
          renderAssessmentReview(result.results, result.score, result.total);
          toast(`Assessment submitted: ${result.score}/${result.total}.`, 'success');
          await loadAssessments();
        } catch (error) { showError(error); button.disabled = false; button.textContent = 'Submit assessment'; }
      });
      target.scrollIntoView({behavior:'smooth', block:'start'});
    } catch (error) { target.textContent = error.message; }
  }
  async function loadAssessmentResults(id) {
    const target = $('#assessmentRunner');
    if (!target) return;
    target.textContent = 'Loading results…';
    try {
      const data = await api(`/api/v1/assessments/${encodeURIComponent(id)}/results`);
      const rows = data.results || [];
      target.innerHTML = `<section class="assessment-result"><h3>${escapeHtml(data.assessment.title)} — class results</h3>${rows.length ? `<div class="table-wrap"><table class="data-table"><thead><tr><th>Student</th><th>Code</th><th>Score</th><th>Percent</th><th>Submitted</th></tr></thead><tbody>${rows.map(row => `<tr><td>${escapeHtml(row.student_name)}</td><td>${escapeHtml(row.student_code)}</td><td>${row.score}/${row.total}</td><td>${row.percent}%</td><td>${escapeHtml(formatDateTime(row.submitted_at))}</td></tr>`).join('')}</tbody></table></div>` : '<p class="muted">No students have submitted this assessment yet.</p>'}</section>`;
      target.scrollIntoView({behavior:'smooth', block:'start'});
    } catch (error) { target.textContent = error.message; }
  }

  function bindStudyLab() {
    $('#practiceNoteOptions')?.addEventListener('change', updatePracticeNoteSelection);
    $('#studyMaterialForm')?.addEventListener('submit', async e => {
      e.preventDefault(); const form = e.currentTarget; const file = $('#studyMaterialFile')?.files?.[0]; const button = $('button[type=submit]', form);
      if (!file || button.disabled) return;
      const data = new FormData(); data.append('file', file); button.disabled = true; button.textContent = 'Uploading…';
      try { const result = await api('/api/v1/study-materials', {method:'POST', body:data}); toast(result.message || 'Notes uploaded.', 'success'); form.reset(); await loadStudyMaterials(); }
      catch (err) { showError(err); }
      finally { button.disabled = false; button.textContent = 'Upload notes'; }
    });
    renderAssessmentDrafts();
    $('#addAssessmentQuestion')?.addEventListener('click', addAssessmentDraft);
    $('#assessmentDraftList')?.addEventListener('click', event => {
      const button = event.target.closest('[data-remove-assessment-question]');
      if (!button) return;
      assessmentDrafts.splice(Number(button.dataset.removeAssessmentQuestion), 1);
      renderAssessmentDrafts();
    });
    $('#assessmentList')?.addEventListener('click', event => {
      const open = event.target.closest('[data-assessment-open]');
      const results = event.target.closest('[data-assessment-results]');
      if (open) openAssessment(open.dataset.assessmentOpen);
      if (results) loadAssessmentResults(results.dataset.assessmentResults);
    });
    $('#refreshAssessments')?.addEventListener('click', () => loadAssessments().catch(showError));
    $('#startPractice')?.addEventListener('click',()=>beginStudyQuiz('practice'));
    $('#startMockTest')?.addEventListener('click',()=>beginStudyQuiz('mock'));
    $('#studyChatForm')?.addEventListener('submit', async e=>{
      e.preventDefault();
      const form=e.currentTarget;
      const input=$('#studyQuestion');
      const button=$('button[type=submit]',form);
      const question=input.value.trim();
      if(!question || button.disabled)return;
      addChatMessage('student',question);
      input.value='';
      button.disabled=true; button.textContent='Thinking…';
      const pending=document.createElement('div'); pending.className='study-message tutor'; pending.setAttribute('role','status'); pending.textContent='Study Buddy is preparing an answer…';
      $('#studyChatLog')?.append(pending);
      try {
        const result=await api('/api/v1/study-chat',{method:'POST',body:JSON.stringify({question})});
        pending.remove(); addChatMessage('tutor',result.answer || 'I could not produce an answer. Please try rephrasing your question.');
      } catch(error) {
        pending.remove();
        // Keep the limited offline helper available only when the AI endpoint is unreachable;
        // do not imply this fallback can answer arbitrary questions.
        const fallback=tutorReply(question);
        const text=error.message.includes('not configured')
          ? error.message
          : `${error.message}\n\nQuick built-in hint: ${fallback}`;
        addChatMessage('tutor',text);
      } finally {
        button.disabled=false; button.textContent='Ask Study Buddy'; input.focus();
      }
    });
    renderStudyHistory();
  }

  function bindInteractions() {
    $$('.nav-link[data-section]').forEach(button => button.addEventListener('click', () => goToSection(button.dataset.section)));
    $$('[data-go]').forEach(button => button.addEventListener('click', () => goToSection(button.dataset.go)));
    $('#mobileMenu')?.addEventListener('click', () => $('#sidebar').classList.toggle('mobile-open'));
    bindStudyLab();
    document.addEventListener('click', event => {
      const target = event.target.closest('.attend-session');
      if (target) { goToSection('attendance'); $('#attendanceSession').value = target.dataset.sessionId; openAttendance(target.dataset.sessionId).catch(showError); }
      const cancel = event.target.closest('.cancel-session');
      if (cancel && confirm('Cancel this class session? Existing attendance records will be retained.')) {
        api(`/api/v1/sessions/${cancel.dataset.sessionId}`, { method: 'PATCH', body: JSON.stringify({ status: 'cancelled' }) }).then(async () => { toast('Class session cancelled.', 'success'); await loadTimetable(); }).catch(showError);
      }
    });
    $('#timetableDate')?.addEventListener('change', () => loadTimetable($('#timetableDate').value).catch(showError));
    $('#refreshSessions')?.addEventListener('click', () => loadTimetable().catch(showError));
    $('#loadAttendance')?.addEventListener('click', () => openAttendance($('#attendanceSession').value).catch(showError));
    $('#refreshMyAttendance')?.addEventListener('click', () => loadMyAttendance().catch(showError));
    $('#attendanceDate')?.addEventListener('change', () => loadSessionsForAttendance().catch(showError));
    $('#loadReport')?.addEventListener('click', () => loadReport().catch(showError));
    $('#refreshAssignments')?.addEventListener('click', () => loadAssignments().catch(showError));
    $('#refreshNotices')?.addEventListener('click', () => loadNotices().catch(showError));
    $('#refreshClasses')?.addEventListener('click', () => loadManagement().catch(showError));
    $('#refreshFeedback')?.addEventListener('click', () => loadFeedback().catch(showError));
    $('#refreshSubjects')?.addEventListener('click', () => loadClassSubjects($('#subjectClass')?.value, true).catch(showError));
    $('#refreshClassTeachers')?.addEventListener('click', () => loadClassTeachers($('#classTeacherClass')?.value).catch(showError));
    $('#subjectClass')?.addEventListener('change', () => loadClassSubjects($('#subjectClass').value, true).catch(showError));
    $('#classTeacherClass')?.addEventListener('change', () => loadClassTeachers($('#classTeacherClass').value).catch(showError));
    $('#sessionClass')?.addEventListener('change', () => loadClassSubjects($('#sessionClass').value, false).catch(showError));
    $('#assignmentClass')?.addEventListener('change', () => loadClassSubjects($('#assignmentClass').value, false).catch(showError));

    $('#themeToggle')?.addEventListener('click', () => {
      const dark = !document.documentElement.classList.contains('dark-mode');
      document.documentElement.classList.toggle('dark-mode', dark);
      document.documentElement.classList.toggle('light-theme', !dark);
      try { localStorage.setItem('ngg_theme', dark ? 'dark' : 'light'); } catch (_) { /* Theme preference is optional. */ }
      const button = $('#themeToggle');
      if (button) {
        button.textContent = dark ? '☼' : '◐';
        button.title = dark ? 'Switch to light theme' : 'Switch to dark theme';
        button.setAttribute('aria-label', button.title);
      }
      const themeMeta = $('meta[name="theme-color"]');
      if (themeMeta) themeMeta.content = dark ? '#111526' : '#f4f7fc';
    });

    bindForm('subjectForm', async () => {
      const classId = $('#subjectClass').value;
      const name = $('#subjectName').value.trim();
      await api(`/api/v1/classes/${encodeURIComponent(classId)}/subjects`, {
        method: 'POST', body: JSON.stringify({ name })
      });
      $('#subjectName').value = '';
      toast('Subject added to class.', 'success');
      await loadClassSubjects(classId, true);
      await loadClassSubjects($('#sessionClass')?.value, false);
      await loadClassSubjects($('#assignmentClass')?.value, false);
    });
    bindForm('classTeacherForm', async () => {
      const classId = $('#classTeacherClass').value;
      await api(`/api/v1/classes/${encodeURIComponent(classId)}/teachers`, {
        method: 'POST', body: JSON.stringify({ teacher_id: $('#classTeacherUser').value })
      });
      toast('Teacher assigned to class.', 'success');
      await loadClassTeachers(classId);
    });
    bindForm('studentImportForm', async () => {
      const file = $('#studentImportFile')?.files?.[0];
      if (!$('#studentImportClass')?.value) throw new Error('Choose a class or batch first.');
      if (!file) throw new Error('Choose a CSV or Excel spreadsheet.');
      const rows = await readStudentSpreadsheet(file);
      if (!rows.length) throw new Error('No student rows were found in that file.');
      renderStudentImportPreview(rows);
      $('#studentImportResult').hidden = true;
      toast(`Preview ready for ${rows.length} student rows. Review before importing.`, 'success');
    });
    $('#studentImportPreview')?.addEventListener('click', event => {
      if (event.target.closest('#confirmStudentImport')) confirmStudentImport();
      if (event.target.closest('#cancelStudentImport')) {
        pendingStudentImportRows = [];
        $('#studentImportPreview').hidden = true;
        $('#studentImportPreview').innerHTML = '';
      }
    });
    $('#studentImportResult')?.addEventListener('click', event => {
      if (event.target.closest('#downloadImportCredentials')) downloadTemporaryCredentials();
    });
    const themeToggle = $('#themeToggle');
    if (themeToggle) {
      const dark = document.documentElement.classList.contains('dark-mode');
      themeToggle.textContent = dark ? '☼' : '◐';
      themeToggle.title = dark ? 'Switch to light theme' : 'Switch to dark theme';
      themeToggle.setAttribute('aria-label', themeToggle.title);
    }

    bindForm('sessionForm', async () => {
      const payload = { class_id: $('#sessionClass').value, subject: $('#sessionSubject').value.trim(), teacher_id: $('#sessionTeacher').value || null,
        room: $('#sessionRoom').value.trim(), starts_at: $('#sessionStarts').value, ends_at: $('#sessionEnds').value };
      await api('/api/v1/sessions', { method: 'POST', body: JSON.stringify(payload) });
      toast('Class session scheduled.', 'success');
      $('#sessionSubject').value = ''; $('#sessionRoom').value = '';
      await loadTimetable($('#timetableDate').value || todayLocal());
      await loadDashboard();
    });
    bindForm('attendanceForm', async () => {
      if (!state.attendanceSession) throw new Error('Open a class register first.');
      const rows = $$('#attendanceRoster tbody tr');
      const records = rows.map(row => ({ student_id: Number(row.dataset.studentId), status: $('.attendance-status', row).value })).filter(record => record.status);
      if (!records.length) throw new Error('Choose a status for at least one student.');
      await api(`/api/v1/sessions/${state.attendanceSession}/attendance`, { method: 'PUT', body: JSON.stringify({ records }) });
      toast(`Saved attendance for ${records.length} student${records.length === 1 ? '' : 's'}.`, 'success');
      await openAttendance(state.attendanceSession);
    });
    bindForm('assignmentForm', async () => {
      await api('/api/v1/assignments', { method: 'POST', body: JSON.stringify({ class_id: $('#assignmentClass').value, subject: $('#assignmentSubject').value.trim(), title: $('#assignmentTitle').value.trim(), instructions: $('#assignmentInstructions').value.trim(), due_at: $('#assignmentDue').value || null }) });
      toast('Assignment published.', 'success'); $('#assignmentForm').reset();
      await loadAssignments(); await loadDashboard();
    });
    bindForm('noticeForm', async () => {
      await api('/api/v1/notices', { method: 'POST', body: JSON.stringify({ title: $('#noticeTitle').value.trim(), body: $('#noticeBody').value.trim(), class_id: $('#noticeClass').value === 'all' ? null : $('#noticeClass').value }) });
      toast('Notice published.', 'success'); $('#noticeForm').reset();
      await loadNotices(); await loadDashboard();
    });
    bindForm('classForm', async () => {
      await api('/api/v1/classes', { method: 'POST', body: JSON.stringify({ name: $('#className').value.trim(), kind: $('#classKind').value, academic_year: $('#classYear').value.trim() }) });
      toast('Class created.', 'success'); $('#classForm').reset(); await loadManagement();
    });
    bindForm('userForm', async () => {
      const data = await api('/api/v1/users', { method: 'POST', body: JSON.stringify({ name: $('#userName').value.trim(), email: $('#userEmail').value.trim(), role: $('#userRole').value, password: $('#userPassword').value }) });
      toast(`${data.user.role === 'teacher' ? 'Teacher' : 'Student'} account created. Share the credentials securely. Password reset is not included in this MVP.`, 'success'); $('#userForm').reset(); await loadManagement();
    });
    bindForm('enrollmentForm', async () => {
      await api(`/api/v1/classes/${$('#enrollClass').value}/enrollments`, { method: 'POST', body: JSON.stringify({ student_id: $('#enrollStudent').value }) });
      toast('Student enrolled.', 'success'); await loadManagement();
    });
    bindForm('assessmentForm', async () => {
      if (!assessmentDrafts.length) throw new Error('Add at least one question before publishing.');
      const payload = {
        class_id: $('#assessmentClass').value,
        title: $('#assessmentTitle').value.trim(),
        instructions: $('#assessmentInstructions').value.trim(),
        due_at: $('#assessmentDue').value || null,
        questions: assessmentDrafts
      };
      const response = await api('/api/v1/assessments', {method:'POST', body:JSON.stringify(payload)});
      assessmentDrafts = [];
      $('#assessmentForm').reset();
      renderAssessmentDrafts();
      toast(response.message || 'Assessment published.', 'success');
      await loadAssessments();
    });
    bindForm('feedbackForm', async () => {
      const payload = {
        category: $('#feedbackCategory').value,
        page: $('#feedbackPage').value.trim() || 'dashboard',
        message: $('#feedbackMessage').value.trim()
      };
      await api('/api/v1/feedback', { method: 'POST', body: JSON.stringify(payload) });
      toast('Thanks—your feedback has been sent for review.', 'success');
      $('#feedbackForm').reset();
      if (state.user?.role === 'admin') await loadFeedback();
    });
    bindForm('changePasswordForm', async () => {
      const newPassword = $('#newPassword').value;
      if (newPassword !== $('#confirmPassword').value) throw new Error('The new passwords do not match.');
      await api('/api/v1/auth/change-password', {
        method: 'POST',
        body: JSON.stringify({ current_password: $('#currentPassword').value, new_password: newPassword })
      });
      $('#changePasswordForm').reset();
      toast('Password changed successfully.', 'success');
    });
    window.addEventListener('online', () => { if ($('#connectionStatus')) { $('#connectionStatus').classList.remove('offline'); $('#connectionStatus').lastChild.textContent = ' Connected'; } });
    window.addEventListener('offline', () => { if ($('#connectionStatus')) { $('#connectionStatus').classList.add('offline'); $('#connectionStatus').lastChild.textContent = ' Offline'; } });
    window.addEventListener('beforeinstallprompt', event => {
      event.preventDefault(); state.deferredInstall = event;
      const install = $('#installButton'); if (install) install.hidden = false;
    });
    $('#installButton')?.addEventListener('click', async () => {
      if (!state.deferredInstall) return;
      state.deferredInstall.prompt();
      await state.deferredInstall.userChoice;
      state.deferredInstall = null; $('#installButton').hidden = true;
    });
  }

  async function bootDashboard() {
    try {
      const meData = await api('/api/v1/auth/me');
      state.user = meData.user;
      state.institution = meData.institution;
      rememberSignedInAccount();
      applyRoleVisibility();
      renderStudyHistory();
      await loadClassesAndUsers();
      $('#timetableDate').value = todayLocal();
      $('#attendanceDate').value = todayLocal();
      const start = new Date(); start.setMinutes(0, 0, 0); start.setHours(start.getHours() + 1);
      const end = new Date(start.getTime() + 60 * 60 * 1000);
      $('#sessionStarts').value = dateTimeLocalValue(start);
      $('#sessionEnds').value = dateTimeLocalValue(end);
      await loadDashboard();
      await loadAssessments();
      await loadTimetable(todayLocal());
      if (state.user.role === 'student') await loadMyAttendance();
      if (state.user.role === 'admin') await loadManagement();
    } catch (error) { showError(error); }
  }

  async function registerServiceWorker() {
    if (!('serviceWorker' in navigator)) return;
    try { await navigator.serviceWorker.register('/sw.js', { scope: '/' }); }
    catch (error) { console.warn('Service worker could not be registered:', error); }
  }

  document.addEventListener('DOMContentLoaded', () => {
    if ($('#appShell')) { bindInteractions(); bootDashboard(); }
    else bindLoginAccounts();
    registerServiceWorker();
  });
})();
