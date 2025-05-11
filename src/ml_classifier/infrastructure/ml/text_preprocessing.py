"""Text preprocessing for ML models."""
from typing import Any, List, Optional, Set, Union

import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer, WordNetLemmatizer
from nltk.tokenize import word_tokenize
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer


class TextPreprocessingStep:
    """Base class for text preprocessing steps."""

    def process(self, text: Union[str, List[str]]) -> Union[str, List[str]]:
        """
        Process the input text.

        Args:
            text: Input text or list of texts

        Returns:
            Processed text or list of texts
        """
        raise NotImplementedError("Subclasses must implement this method")

    def fit(self, texts: List[str]) -> "TextPreprocessingStep":
        """
        Fit the preprocessing step on a corpus of texts.

        Args:
            texts: List of texts to fit on

        Returns:
            Self for chaining
        """
        return self


class LowercaseConverter(TextPreprocessingStep):
    """Converts text to lowercase."""

    def process(self, text: Union[str, List[str]]) -> Union[str, List[str]]:
        """Convert text to lowercase."""
        if isinstance(text, list):
            return [t.lower() for t in text]
        return text.lower()


class Tokenizer(TextPreprocessingStep):
    """Tokenizes text into words."""

    def __init__(self, pattern: str = r"\b\w+\b"):
        """
        Initialize tokenizer.

        Args:
            pattern: Regex pattern for tokenization
        """
        self.pattern = pattern
        # Download NLTK data if needed
        try:
            nltk.data.find("tokenizers/punkt")
        except LookupError:
            nltk.download("punkt")

    def process(self, text: Union[str, List[str]]) -> Union[List[str], List[List[str]]]:
        """Tokenize text into words."""
        if isinstance(text, list):
            return [word_tokenize(t) for t in text]
        return word_tokenize(text)


class StopwordRemover(TextPreprocessingStep):
    """Removes stopwords from tokenized text."""

    def __init__(
        self, language: str = "english", additional_stopwords: Optional[Set[str]] = None
    ):
        """
        Initialize stopword remover.

        Args:
            language: Language for stopwords
            additional_stopwords: Additional stopwords to remove
        """
        # Download stopwords if needed
        try:
            nltk.data.find("corpora/stopwords")
        except LookupError:
            nltk.download("stopwords")

        self.stopwords = set(stopwords.words(language))
        if additional_stopwords:
            self.stopwords.update(additional_stopwords)

    def process(
        self, tokens: Union[List[str], List[List[str]]]
    ) -> Union[List[str], List[List[str]]]:
        """Remove stopwords from tokenized text."""
        if all(isinstance(item, list) for item in tokens):
            return [
                [token for token in sent if token.lower() not in self.stopwords]
                for sent in tokens
            ]
        return [token for token in tokens if token.lower() not in self.stopwords]


class Stemmer(TextPreprocessingStep):
    """Stems words using Porter stemmer."""

    def __init__(self):
        """Initialize stemmer."""
        self.stemmer = PorterStemmer()

    def process(
        self, tokens: Union[List[str], List[List[str]]]
    ) -> Union[List[str], List[List[str]]]:
        """Stem tokens."""
        if all(isinstance(item, list) for item in tokens):
            return [[self.stemmer.stem(token) for token in sent] for sent in tokens]
        return [self.stemmer.stem(token) for token in tokens]


class Lemmatizer(TextPreprocessingStep):
    """Lemmatizes words using WordNet lemmatizer."""

    def __init__(self, pos: str = "n"):
        """
        Initialize lemmatizer.

        Args:
            pos: Part of speech tag ('n' for noun, 'v' for verb, etc.)
        """
        # Download WordNet if needed
        try:
            nltk.data.find("corpora/wordnet")
        except LookupError:
            nltk.download("wordnet")

        self.lemmatizer = WordNetLemmatizer()
        self.pos = pos

    def process(
        self, tokens: Union[List[str], List[List[str]]]
    ) -> Union[List[str], List[List[str]]]:
        """Lemmatize tokens."""
        if all(isinstance(item, list) for item in tokens):
            return [
                [self.lemmatizer.lemmatize(token, self.pos) for token in sent]
                for sent in tokens
            ]
        return [self.lemmatizer.lemmatize(token, self.pos) for token in tokens]


class JoinerStep(TextPreprocessingStep):
    """Joins tokens back into text."""

    def __init__(self, separator: str = " "):
        """
        Initialize joiner.

        Args:
            separator: String to use for joining tokens
        """
        self.separator = separator

    def process(
        self, tokens: Union[List[str], List[List[str]]]
    ) -> Union[str, List[str]]:
        """Join tokens into text."""
        if all(isinstance(item, list) for item in tokens):
            return [self.separator.join(sent) for sent in tokens]
        return self.separator.join(tokens)


class VectorizerStep(TextPreprocessingStep):
    """Vectorizes text using TF-IDF or CountVectorizer."""

    def __init__(
        self,
        vectorizer_type: str = "tfidf",
        max_features: Optional[int] = None,
        ngram_range: tuple = (1, 1),
        **kwargs,
    ):
        """
        Initialize vectorizer.

        Args:
            vectorizer_type: Type of vectorizer ('tfidf' or 'count')
            max_features: Maximum number of features
            ngram_range: Range of n-grams to consider
            **kwargs: Additional arguments for vectorizer
        """
        self.vectorizer_type = vectorizer_type
        if vectorizer_type.lower() == "tfidf":
            self.vectorizer = TfidfVectorizer(
                max_features=max_features, ngram_range=ngram_range, **kwargs
            )
        elif vectorizer_type.lower() == "count":
            self.vectorizer = CountVectorizer(
                max_features=max_features, ngram_range=ngram_range, **kwargs
            )
        else:
            raise ValueError(f"Unsupported vectorizer type: {vectorizer_type}")

    def fit(self, texts: List[str]) -> "VectorizerStep":
        """Fit vectorizer on texts."""
        self.vectorizer.fit(texts)
        return self

    def process(self, texts: Union[str, List[str]]) -> Any:
        """Transform texts to feature vectors."""
        if isinstance(texts, str):
            texts = [texts]
        return self.vectorizer.transform(texts)


class TextPreprocessor:
    """Pipeline for text preprocessing."""

    def __init__(self, steps: Optional[List[TextPreprocessingStep]] = None):
        """
        Initialize text preprocessor.

        Args:
            steps: List of preprocessing steps
        """
        self.steps = steps or []

    def add_step(self, step: TextPreprocessingStep) -> "TextPreprocessor":
        """
        Add a preprocessing step.

        Args:
            step: Preprocessing step to add

        Returns:
            Self for chaining
        """
        self.steps.append(step)
        return self

    def fit(self, texts: List[str]) -> "TextPreprocessor":
        """
        Fit all steps on a corpus of texts.

        Args:
            texts: List of texts to fit on

        Returns:
            Self for chaining
        """
        processed_texts = texts
        for step in self.steps:
            step.fit(processed_texts)
            processed_texts = step.process(processed_texts)
        return self

    def process(self, text: Union[str, List[str]]) -> Any:
        """
        Process text through all steps.

        Args:
            text: Input text or list of texts

        Returns:
            Processed output
        """
        current = text
        for step in self.steps:
            current = step.process(current)
        return current

    @classmethod
    def create_default_pipeline(cls, lang: str = "english") -> "TextPreprocessor":
        """
        Create a default preprocessing pipeline.

        Args:
            lang: Language for stopwords

        Returns:
            TextPreprocessor with default steps
        """
        return cls(
            [
                LowercaseConverter(),
                Tokenizer(),
                StopwordRemover(language=lang),
                Lemmatizer(),
                JoinerStep(),
            ]
        )
