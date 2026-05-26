import re
from decimal import Decimal, InvalidOperation
from typing import Tuple
from app.bundle.schema import AnalysisBundle

class FactGuardrail:
    @staticmethod
    def evaluate(text: str, bundle: AnalysisBundle) -> Tuple[bool, str]:
        """
        Verifies all numbers in the generated text exist in bundle.metrics.
        Returns a tuple of (is_valid, error_message).
        """
        # Find all numbers in the text (simple regex for floats/ints)
        numbers_in_text = set(re.findall(r'(?<![A-Za-z])-?\d+(?:\.\d+)?(?![A-Za-z])', text))
        
        approved_numbers = FactGuardrail._collect_numbers(bundle.metrics)
        approved_numbers.update(FactGuardrail._collect_numbers(bundle.analysis_results))
        
        hallucinated = []
        for num in numbers_in_text:
            # We ignore small integers that might be list numbers (1, 2, 3...) or years
            unsigned_num = num.lstrip("-")
            if '.' not in unsigned_num and len(unsigned_num) < 3 and int(num) < 10:
                continue
            if len(unsigned_num) == 4 and unsigned_num.startswith('20'):
                continue
                
            if FactGuardrail._normalize_number(num) not in approved_numbers:
                hallucinated.append(num)
                
        if hallucinated:
            return False, f"Hallucination detected: The following numbers are not in the AnalysisBundle metrics: {', '.join(hallucinated)}"
            
        return True, ""

    @staticmethod
    def _normalize_number(value: str) -> str:
        try:
            return str(Decimal(value).normalize())
        except (InvalidOperation, ValueError):
            return value

    @staticmethod
    def _collect_numbers(value) -> set[str]:
        if isinstance(value, bool) or value is None:
            return set()
        if isinstance(value, (int, float, Decimal)):
            return {FactGuardrail._normalize_number(str(value))}
        if isinstance(value, dict):
            numbers = set()
            for child in value.values():
                numbers.update(FactGuardrail._collect_numbers(child))
            return numbers
        if isinstance(value, list):
            numbers = set()
            for child in value:
                numbers.update(FactGuardrail._collect_numbers(child))
            return numbers
        return set()
