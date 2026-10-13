"""Pure unit tests for the course-note helper functions; no Flask install required."""
import unittest

from study_content import chunk_note_text, retrieve_relevant_chunks, stored_material_metadata


class StudyContentTests(unittest.TestCase):
    def test_stored_filename_preserves_opaque_id_and_original_extension(self):
        doc_id, name = stored_material_metadata("0123456789abcdef__NLP-chapter.pdf.txt")
        self.assertEqual(doc_id, "0123456789abcdef")
        self.assertEqual(name, "NLP-chapter.pdf")

    def test_malformed_stored_filename_is_rejected(self):
        self.assertEqual(stored_material_metadata("notes.txt"), ("", ""))
        self.assertEqual(stored_material_metadata("../../bad__notes.txt"), ("", ""))

    def test_single_long_paragraph_is_split_and_later_topic_is_retrievable(self):
        intro = "Introductory material about general study skills and classroom learning. " * 50
        target = "TF-IDF weights a term by its frequency in a document and rarity across documents. "
        text = intro + target * 30
        chunks = chunk_note_text(text, max_chars=700, overlap=80)
        self.assertGreater(len(chunks), 2)
        context = retrieve_relevant_chunks([{"name": "NLP.txt", "text": text}], "Explain TF-IDF term frequency rarity", limit=3)
        self.assertIn("TF-IDF", context)
        self.assertIn("NLP.txt", context)

    def test_unicode_notes_can_be_retrieved(self):
        context = retrieve_relevant_chunks(
            [{"name": "Hindi notes.txt", "text": "प्रकाश संश्लेषण पौधों में भोजन बनाने की प्रक्रिया है। यह सूर्य के प्रकाश का उपयोग करता है।"}],
            "प्रकाश संश्लेषण प्रक्रिया", limit=2,
        )
        self.assertIn("प्रकाश संश्लेषण", context)

    def test_retrieval_is_bounded_and_empty_questions_return_no_context(self):
        text = ("neural network learning model " + "data science practice " * 500) * 3
        context = retrieve_relevant_chunks([{"name": "ML.txt", "text": text}], "neural network learning", limit=2, max_context_chars=1000)
        self.assertLessEqual(len(context), 1000)
        self.assertEqual(retrieve_relevant_chunks([{"name": "ML.txt", "text": text}], "the and why", limit=2), "")


if __name__ == "__main__":
    unittest.main()
