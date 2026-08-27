from src.extraction.skill_normalizer import SkillNormalizer


def test_common_skill_aliases():
    normalizer = SkillNormalizer()

    tests = [
        ("JS", "javascript"),
        ("JavaScript", "javascript"),
        ("React.js", "react"),
        ("ReactJS", "react"),
        ("React Native", "react_native"),
        ("react-native", "react_native"),
        ("NodeJS", "node.js"),
        ("TS", "typescript"),
        ("Python3", "python"),
    ]

    for original, expected in tests:
        assert normalizer.normalize(original) == expected


def test_similar_skills_are_not_confused():
    normalizer = SkillNormalizer()

    assert normalizer.normalize("Java") != normalizer.normalize("JavaScript")
    assert normalizer.normalize("React") != normalizer.normalize("React Native")