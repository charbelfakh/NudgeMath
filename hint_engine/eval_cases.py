from hint_engine.models import EvalCase

EVAL_CASES: list[EvalCase] = [
    EvalCase(
        case_id="algebra_sign_error",
        problem="Solve for x: 2x - 5 = 9",
        student_answer="x = 2",
        correct_answer="x = 7",
        expectations={
            "must_not_reveal_answer": True,
            "must_address_the_specific_error": True,
        },
    ),
    EvalCase(
        case_id="order_of_operations",
        problem="Evaluate: 2 + 3 × 4",
        student_answer="20",
        correct_answer="14",
        expectations={
            "must_not_reveal_answer": True,
            "must_address_the_specific_error": True,
        },
    ),
    EvalCase(
        case_id="fraction_comparison",
        problem="Which is larger: 2/3 or 3/5? Explain.",
        student_answer="3/5 is larger because 3 > 2",
        correct_answer="2/3 is larger",
        expectations={
            "must_not_reveal_answer": True,
            "must_address_the_specific_error": True,
        },
    ),
    EvalCase(
        case_id="distribute_negative_sign",
        problem="Expand: -(3x - 2)",
        student_answer="-3x - 2",
        correct_answer="-3x + 2",
        expectations={
            "must_not_reveal_answer": True,
            "must_address_the_specific_error": True,
        },
    ),
    EvalCase(
        case_id="combining_unlike_terms",
        problem="Simplify: 2x + 3y + 5x",
        student_answer="7xy",
        correct_answer="7x + 3y",
        expectations={
            "must_not_reveal_answer": True,
            "must_address_the_specific_error": True,
        },
    ),
    EvalCase(
        case_id="percentage_confusion",
        problem="What is 25% of 60?",
        student_answer="1500",
        correct_answer="15",
        expectations={
            "must_not_reveal_answer": True,
            "must_address_the_specific_error": True,
        },
    ),
    EvalCase(
        case_id="units_conversion",
        problem="Convert 1.2 kilometers to meters.",
        student_answer="120",
        correct_answer="1200",
        expectations={
            "must_not_reveal_answer": True,
            "must_address_the_specific_error": True,
        },
    ),
    EvalCase(
        case_id="exponent_multiply_rule",
        problem="Simplify: 2³ × 2²",
        student_answer="2⁶",
        correct_answer="2⁵",
        expectations={
            "must_not_reveal_answer": True,
            "must_address_the_specific_error": True,
        },
    ),
    EvalCase(
        case_id="decimal_multiplication",
        problem="Calculate: 0.5 × 0.3",
        student_answer="1.5",
        correct_answer="0.15",
        expectations={
            "must_not_reveal_answer": True,
            "must_address_the_specific_error": True,
        },
    ),
    EvalCase(
        case_id="fraction_addition",
        problem="Compute: 1/2 + 1/3",
        student_answer="2/5",
        correct_answer="5/6",
        expectations={
            "must_not_reveal_answer": True,
            "must_address_the_specific_error": True,
        },
    ),
]
