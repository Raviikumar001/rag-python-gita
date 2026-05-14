import pytest

from app.api.models import QuestionQuery, SearchQuery


class TestQuestionQuery:
    def test_valid_query(self):
        q = QuestionQuery(question="What is dharma?")
        assert q.question == "What is dharma?"
        assert q.context_limit == 5
        assert q.stream is False

    def test_context_limit_bounds(self):
        with pytest.raises(ValueError):
            QuestionQuery(question="test", context_limit=0)

        with pytest.raises(ValueError):
            QuestionQuery(question="test", context_limit=21)

    def test_chapter_filter_bounds(self):
        with pytest.raises(ValueError):
            QuestionQuery(question="test", chapter_filter=0)

        with pytest.raises(ValueError):
            QuestionQuery(question="test", chapter_filter=19)

    def test_empty_question(self):
        with pytest.raises(ValueError):
            QuestionQuery(question="")


class TestSearchQuery:
    def test_valid_search(self):
        q = SearchQuery(query="karma yoga")
        assert q.query == "karma yoga"
        assert q.k == 5
