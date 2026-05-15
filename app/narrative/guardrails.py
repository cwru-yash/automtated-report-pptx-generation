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
        numbers_in_text = set(re.findall(r'\b\d+(?:\.\d+)?\b', text))
        
        metric_values = {FactGuardrail._normalize_number(str(v)) for v in bundle.metrics.values()}
        
        hallucinated = []
        for num in numbers_in_text:
            # We ignore small integers that might be list numbers (1, 2, 3...) or years
            if '.' not in num and len(num) < 3 and int(num) < 10:
                continue
            if len(num) == 4 and num.startswith('20'):
                continue
                
            if FactGuardrail._normalize_number(num) not in metric_values:
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
