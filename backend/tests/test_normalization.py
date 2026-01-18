from api.utils import normalize_url

def test_normalization():
    cases = [
        ("https://example.com/", "https://example.com"),
        ("https://Example.com/Foo", "https://example.com/Foo"), # Host lower, path mixed case preserved
        ("https://example.com/foo/", "https://example.com/foo"),
        ("http://test.com", "http://test.com"),
        ("https://example.com?q=1", "https://example.com?q=1"),
        ("https://example.com/?q=1", "https://example.com?q=1"),
    ]
    
    for input_url, expected in cases:
        result = normalize_url(input_url)
        print(f"Input: {input_url} -> Output: {result}")
        assert result == expected, f"Failed: {input_url} -> {result}, expected {expected}"
        
    print("All normalization tests passed!")

if __name__ == "__main__":
    test_normalization()
