from datetime import date
from django.core.exceptions import ValidationError
from django.test import TestCase
from apps.benchmarking.models import BenchmarkFramework, BenchmarkPerformanceLevel


class BenchmarkModelTests(TestCase):
    def test_performance_ranges_cannot_overlap(self):
        framework = BenchmarkFramework.objects.create(name="F", code="F", effective_from=date.today())
        BenchmarkPerformanceLevel.objects.create(framework=framework, name="Good", minimum_score=75, maximum_score=100)
        overlapping = BenchmarkPerformanceLevel(framework=framework, name="Average", minimum_score=60, maximum_score=80)
        with self.assertRaises(ValidationError): overlapping.full_clean()
