"""Unit tests for slug utility functions."""

from __future__ import annotations

import pytest

from app.utils.slug import generate_slug_variants, normalize_for_cache, slugify


class TestSlugify:
    """Test the slugify function."""

    def test_basic_space_replacement(self) -> None:
        """Test basic space to hyphen conversion."""
        assert slugify("Hello World") == "hello-world"
        assert slugify("Test Name") == "test-name"

    def test_underscore_replacement(self) -> None:
        """Test underscore to hyphen conversion."""
        assert slugify("Test_Name") == "test-name"
        assert slugify("my_variable") == "my-variable"

    def test_mixed_separators(self) -> None:
        """Test mixed spaces and underscores."""
        assert slugify("Mixed Test_Name") == "mixed-test-name"
        assert slugify("Complex_Name With Spaces") == "complex-name-with-spaces"
        assert slugify("test_file name.txt") == "test-file-name.txt"

    def test_lowercase_conversion(self) -> None:
        """Test uppercase to lowercase conversion."""
        assert slugify("UPPERCASE") == "uppercase"
        assert slugify("CamelCase") == "camelcase"
        assert slugify("Mixed_CASE_Name") == "mixed-case-name"

    def test_already_hyphenated(self) -> None:
        """Test strings that are already hyphenated."""
        assert slugify("already-hyphenated") == "already-hyphenated"
        assert slugify("kebab-case-string") == "kebab-case-string"

    def test_special_characters_preserved(self) -> None:
        """Test that non-space/underscore characters are preserved."""
        assert slugify("test.file") == "test.file"
        assert slugify("email@domain.com") == "email@domain.com"
        assert slugify("version-1.2.3") == "version-1.2.3"

    def test_multiple_separators(self) -> None:
        """Test multiple consecutive separators."""
        assert slugify("test  name") == "test--name"
        assert slugify("test__name") == "test--name"
        assert slugify("test _ name") == "test---name"

    def test_empty_and_edge_cases(self) -> None:
        """Test empty strings and edge cases."""
        assert slugify("") == ""
        assert slugify(" ") == "-"
        assert slugify("_") == "-"
        assert slugify("a") == "a"


class TestGenerateSlugVariants:
    """Test the generate_slug_variants function."""

    def test_hyphenated_input(self) -> None:
        """Test variant generation from hyphenated slug."""
        variants = generate_slug_variants("hello-world")
        assert variants == ["hello world", "hello-world", "hello_world"]

    def test_underscore_input(self) -> None:
        """Test variant generation from underscore slug."""
        variants = generate_slug_variants("test_name")
        assert variants == ["test name", "test_name", "test-name"]

    def test_space_input(self) -> None:
        """Test variant generation from space slug."""
        variants = generate_slug_variants("hello world")
        # When input is already space-separated, variants are deduplicated to just the original
        assert variants == ["hello world"]

    def test_mixed_separators_input(self) -> None:
        """Test variant generation from mixed separator slug."""
        variants = generate_slug_variants("test-name_value")
        assert variants == ["test name value", "test-name_value", "test-name-value", "test_name_value"]

    def test_no_separators(self) -> None:
        """Test variant generation from slug without separators."""
        variants = generate_slug_variants("singleword")
        assert variants == ["singleword"]

    def test_empty_input(self) -> None:
        """Test variant generation from empty string."""
        variants = generate_slug_variants("")
        assert variants == []

    def test_none_input(self) -> None:
        """Test variant generation from None input."""
        variants = generate_slug_variants(None)  # type: ignore[arg-type]
        assert variants == []

    def test_whitespace_input(self) -> None:
        """Test variant generation from whitespace input."""
        variants = generate_slug_variants("  ")
        assert variants == []

    def test_case_normalization(self) -> None:
        """Test that input is normalized to lowercase."""
        variants = generate_slug_variants("Hello-World")
        assert variants == ["hello world", "hello-world", "hello_world"]

    def test_deduplication(self) -> None:
        """Test that duplicate variants are removed."""
        # Input that would generate duplicates
        variants = generate_slug_variants("test")
        # Should only appear once since no separators to convert
        assert variants == ["test"]

    def test_complex_slug(self) -> None:
        """Test variant generation for complex slug patterns."""
        variants = generate_slug_variants("multi-word_slug-test")
        expected = ["multi word slug test", "multi-word_slug-test", "multi-word-slug-test", "multi_word_slug_test"]
        assert variants == expected


class TestNormalizeForCache:
    """Test the normalize_for_cache function."""

    def test_hyphen_normalization(self) -> None:
        """Test hyphen to space conversion."""
        assert normalize_for_cache("hello-world") == "hello world"
        assert normalize_for_cache("test-name") == "test name"

    def test_underscore_normalization(self) -> None:
        """Test underscore to space conversion."""
        assert normalize_for_cache("test_name") == "test name"
        assert normalize_for_cache("my_variable") == "my variable"

    def test_mixed_separators_normalization(self) -> None:
        """Test mixed separator normalization."""
        assert normalize_for_cache("test-name_value") == "test name value"
        assert normalize_for_cache("complex_slug-with-mixed") == "complex slug with mixed"

    def test_already_spaces(self) -> None:
        """Test normalization of strings that already have spaces."""
        assert normalize_for_cache("hello world") == "hello world"
        assert normalize_for_cache("test name") == "test name"

    def test_case_normalization(self) -> None:
        """Test uppercase to lowercase conversion."""
        assert normalize_for_cache("Hello-World") == "hello world"
        assert normalize_for_cache("UPPER_CASE") == "upper case"
        assert normalize_for_cache("Mixed-Test_Name") == "mixed test name"

    def test_empty_and_none_inputs(self) -> None:
        """Test empty string and None inputs."""
        assert normalize_for_cache("") == ""
        assert normalize_for_cache(None) == ""  # type: ignore[arg-type]

    def test_whitespace_handling(self) -> None:
        """Test handling of whitespace."""
        assert normalize_for_cache("  test-name  ") == "test name"
        assert normalize_for_cache("   ") == ""

    def test_no_separators(self) -> None:
        """Test normalization of strings without separators."""
        assert normalize_for_cache("singleword") == "singleword"
        assert normalize_for_cache("CamelCase") == "camelcase"

    def test_special_characters_preserved(self) -> None:
        """Test that non-separator special characters are preserved."""
        assert normalize_for_cache("test.file-name") == "test.file name"
        assert normalize_for_cache("email@domain_name") == "email@domain name"


class TestSlugUtilsIntegration:
    """Integration tests for slug utility functions working together."""

    def test_slugify_to_variants_workflow(self) -> None:
        """Test the workflow from slugify to variant generation."""
        original_name = "Test Model Name"
        slug = slugify(original_name)
        variants = generate_slug_variants(slug)

        assert slug == "test-model-name"
        assert "test model name" in variants
        assert "test-model-name" in variants
        assert "test_model_name" in variants

    def test_variants_to_cache_normalization(self) -> None:
        """Test normalization of generated variants for cache keys."""
        variants = generate_slug_variants("test-model")
        normalized_variants = [normalize_for_cache(v) for v in variants]

        # All variants should normalize to the same cache key
        expected_cache_key = "test model"
        assert all(norm == expected_cache_key for norm in normalized_variants)

    def test_round_trip_consistency(self) -> None:
        """Test that normalization is consistent regardless of input format."""
        inputs = ["test-name", "test_name", "test name", "Test-Name", "TEST_NAME"]
        normalized = [normalize_for_cache(inp) for inp in inputs]

        # All should normalize to the same value
        assert all(norm == "test name" for norm in normalized)

    @pytest.mark.parametrize(
        "input_name,expected_slug",
        [
            ("Simple Name", "simple-name"),
            ("Complex_Model Name", "complex-model-name"),
            ("UPPERCASE_NAME", "uppercase-name"),
            ("Already-Kebab-Case", "already-kebab-case"),
            ("mixed_CASE-Name", "mixed-case-name"),
            ("Single", "single"),
            ("With.Special@Chars", "with.special@chars"),
        ],
    )
    def test_slugify_parametrized(self, input_name: str, expected_slug: str) -> None:
        """Parametrized test for various slugify inputs."""
        assert slugify(input_name) == expected_slug

    @pytest.mark.parametrize(
        "input_slug,expected_first_variant",
        [
            ("hello-world", "hello world"),
            ("test_name", "test name"),
            ("already spaces", "already spaces"),
            ("mixed-slug_name", "mixed slug name"),
        ],
    )
    def test_variants_first_is_space_normalized(self, input_slug: str, expected_first_variant: str) -> None:
        """Test that the first variant is always space-normalized."""
        variants = generate_slug_variants(input_slug)
        assert variants[0] == expected_first_variant
