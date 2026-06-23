from hint_engine.eval_cases import EVAL_CASES
from hint_engine.models import Hint

# Algebra sign-error case: 2x - 5 = 9, correct answer x = 7
ALGEBRA_CASE = EVAL_CASES[0]

GOOD_ALGEBRA_HINT = Hint(
    hint_text=(
        "When you move -5 to the other side, check whether you added or "
        "subtracted 5 on both sides."
    ),
    reveals_answer=False,
    meta={"fixture": "good_algebra"},
)

BAD_LEAKING_ALGEBRA_HINT = Hint(
    hint_text="After fixing the sign, you'll get x = 7.",
    reveals_answer=False,
    meta={"fixture": "bad_leaking_algebra"},
)

UNPREFIXED_NUMERIC_LEAK = Hint(
    hint_text="After fixing the sign, you'll get 7.",
    reveals_answer=False,
    meta={"fixture": "unprefixed_numeric_leak"},
)

EMPTY_HINT = Hint(
    hint_text="   ",
    reveals_answer=False,
    meta={"fixture": "empty"},
)

OVER_LENGTH_HINT = Hint(
    hint_text="x" * 501,
    reveals_answer=False,
    meta={"fixture": "over_length"},
)

BANNED_PHRASE_HINT = Hint(
    hint_text="The answer is 7, but let's walk through why.",
    reveals_answer=False,
    meta={"fixture": "banned_phrase"},
)
