# apps/contractor/services/performance_service.py

from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
from ..models import (
    Contractor, ContractorPerformanceMetric, ContractorInspection,
    ContractorPreQualification, ContractorDocument, WorkOrder,
    TrainingSignOff, PerformanceWeightConfig,
    OnboardingRequest, OnboardingDocumentRequirement
)


class ContractorPerformanceService:
    """
    Service to calculate contractor performance metrics.
    """
    
    @staticmethod
    def calculate_contractor_performance(contractor, period_month, period_year, period_type='MONTHLY'):
        """
        Calculate performance for a single contractor for a specific period.
        """
        # Get or create metric
        metric, created = ContractorPerformanceMetric.objects.get_or_create(
            contractor=contractor,
            period_type=period_type,
            period_month=period_month,
            period_year=period_year
        )
        
        # 1. Pre-Qualification Score
        pre_qual = ContractorPreQualification.objects.filter(
            contractor=contractor,
            status='APPROVED'
        ).first()
        
        if pre_qual:
            metric.pre_qualification_score = ContractorPerformanceService._calculate_pre_qualification_score(pre_qual)
            metric.risk_level = pre_qual.risk_level
        else:
            metric.pre_qualification_score = 0
        
        # 2. Onboarding Compliance Score
        metric.document_compliance_score = ContractorPerformanceService._calculate_onboarding_compliance(contractor)
        
        # 3. Training Compliance Score
        metric.training_compliance_score = ContractorPerformanceService._calculate_training_compliance(contractor)
        
        # 4. Inspection Compliance Score
        inspection_data = ContractorPerformanceService._calculate_inspection_compliance(
            contractor, period_month, period_year
        )
        metric.inspection_compliance_score = inspection_data['score']
        metric.inspections_count = inspection_data['count']
        
        # 5. Work Order Completion Score
        wo_data = ContractorPerformanceService._calculate_work_order_completion(
            contractor, period_month, period_year
        )
        metric.work_order_completion_score = wo_data['score']
        metric.work_orders_count = wo_data['count']
        
        # 6. Calculate Overall Score
        metric.overall_performance_score = ContractorPerformanceService._calculate_overall_score(metric)
        
        # 7. Determine Rating
        metric.rating = ContractorPerformanceService._get_rating(metric.overall_performance_score)
        
        metric.save()
        
        return metric
    
    @staticmethod
    def _calculate_onboarding_compliance(contractor):
        """
        Calculate onboarding compliance score from onboarding document requirements.
        """
        # Get the latest approved onboarding request for this contractor
        onboarding = OnboardingRequest.objects.filter(
            contractor=contractor,
            status='APPROVED'
        ).order_by('-created_at').first()
        
        if not onboarding:
            return 0
        
        # Get all document requirements for this onboarding
        doc_requirements = OnboardingDocumentRequirement.objects.filter(
            onboarding=onboarding
        )
        
        total = doc_requirements.count()
        if total == 0:
            return 0
        
        # Count documents that are VERIFIED or UPLOADED
        completed = doc_requirements.filter(
            status__in=['VERIFIED', 'UPLOADED']
        ).count()
        
        return (completed / total) * 100
    
    @staticmethod
    def _calculate_pre_qualification_score(pre_qual):
        """Calculate pre-qualification score from the assessment."""
        # If you have a score field, use it directly
        if hasattr(pre_qual, 'score') and pre_qual.score:
            return pre_qual.score
        
        # Otherwise calculate from individual parameters
        score = 0
        weights = {
            'years_of_experience': 15,
            'similar_work_experience': 15,
            'previous_ehs_performance': 15,
            'safety_manpower': 10,
            'has_training_system': 10,
            'has_emergency_preparedness': 10,
            'has_insurance': 15,
            'equipment_capability': 10
        }
        
        # Experience
        if pre_qual.years_of_experience >= 10:
            score += weights['years_of_experience']
        elif pre_qual.years_of_experience >= 5:
            score += weights['years_of_experience'] * 0.7
        elif pre_qual.years_of_experience >= 2:
            score += weights['years_of_experience'] * 0.4
        
        # Safety capability
        if pre_qual.has_safety_policy:
            score += weights['has_training_system'] * 0.5
        if pre_qual.has_training_system:
            score += weights['has_training_system'] * 0.5
        if pre_qual.has_emergency_preparedness:
            score += weights['has_emergency_preparedness']
        if pre_qual.safety_manpower > 0:
            score += min(weights['safety_manpower'], pre_qual.safety_manpower * 2)
        
        # Insurance
        if pre_qual.has_insurance:
            score += weights['has_insurance']
        
        # Equipment capability
        if pre_qual.equipment_capability:
            score += weights['equipment_capability'] * 0.5
        if pre_qual.training_capability:
            score += weights['equipment_capability'] * 0.5
        
        # EHS Performance
        if pre_qual.accident_history == 0:
            score += weights['previous_ehs_performance']
        elif pre_qual.accident_history <= 2:
            score += weights['previous_ehs_performance'] * 0.6
        else:
            score += weights['previous_ehs_performance'] * 0.2
        
        return min(100, score)
    
    @staticmethod
    def _calculate_training_compliance(contractor):
        """Calculate training compliance score."""
        signoffs = TrainingSignOff.objects.filter(
            contractor=contractor,
            status='COMPLETED'
        )
        total = signoffs.count()
        
        if total == 0:
            return 0
        
        # Count completed sign-offs
        completed = signoffs.filter(contractor_declaration=True, company_declaration=True).count()
        return (completed / total) * 100
    
    @staticmethod
    def _calculate_inspection_compliance(contractor, period_month, period_year):
        """Calculate average inspection compliance score."""
        # Get inspections for the period
        start_date = datetime(period_year, period_month, 1).date()
        if period_month == 12:
            end_date = datetime(period_year + 1, 1, 1).date() - timedelta(days=1)
        else:
            end_date = datetime(period_year, period_month + 1, 1).date() - timedelta(days=1)
        
        inspections = ContractorInspection.objects.filter(
            contractor=contractor,
            status='CLOSED',
            closed_at__date__gte=start_date,
            closed_at__date__lte=end_date
        )
        
        count = inspections.count()
        if count == 0:
            return {'score': 0, 'count': 0}
        
        # Calculate average compliance score from responses
        total_score = 0
        for inspection in inspections:
            responses = inspection.responses.all()
            total_questions = inspection.selected_questions.count()
            if total_questions > 0:
                yes_count = responses.filter(answer='YES').count()
                score = (yes_count / total_questions) * 100
                total_score += score
        
        avg_score = total_score / count if count > 0 else 0
        return {'score': round(avg_score, 1), 'count': count}
    
    @staticmethod
    def _calculate_work_order_completion(contractor, period_month, period_year):
        """Calculate work order completion score."""
        start_date = datetime(period_year, period_month, 1).date()
        if period_month == 12:
            end_date = datetime(period_year + 1, 1, 1).date() - timedelta(days=1)
        else:
            end_date = datetime(period_year, period_month + 1, 1).date() - timedelta(days=1)
        
        work_orders = WorkOrder.objects.filter(
            contractor=contractor,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )
        
        count = work_orders.count()
        if count == 0:
            return {'score': 0, 'count': 0}
        
        # Count completed work orders (CLOSED or APPROVED)
        completed = work_orders.filter(status__in=['CLOSED', 'APPROVED']).count()
        score = (completed / count) * 100
        
        return {'score': round(score, 1), 'count': count}
    
    @staticmethod
    def _calculate_overall_score(metric):
        """Calculate weighted overall performance score."""
        # Get active weight configuration
        weight_config = PerformanceWeightConfig.objects.filter(is_active=True).first()
        if not weight_config:
            # Default weights if no config
            weight_config = PerformanceWeightConfig.objects.create(
                weight_pre_qualification=15,
                weight_onboarding_compliance=15,
                weight_training_compliance=20,
                weight_inspection_compliance=25,
                weight_work_order_completion=15
            )
        
        total_weight = weight_config.get_total_weight()
        if total_weight == 0:
            return 0
        
        score = (
            (metric.pre_qualification_score * weight_config.weight_pre_qualification) +
            (metric.document_compliance_score * weight_config.weight_onboarding_compliance) +
            (metric.training_compliance_score * weight_config.weight_training_compliance) +
            (metric.inspection_compliance_score * weight_config.weight_inspection_compliance) +
            (metric.work_order_completion_score * weight_config.weight_work_order_completion)
        ) / total_weight
        
        return round(score, 1)
    
    @staticmethod
    def _get_rating(score):
        """Get rating based on score."""
        if score >= 90:
            return 'Excellent'
        elif score >= 75:
            return 'Good'
        elif score >= 60:
            return 'Needs Improvement'
        else:
            return 'Poor'


class BulkPerformanceCalculator:
    """
    Calculate performance for all contractors or a group.
    """
    
    @staticmethod
    def calculate_all_contractors(period_month=None, period_year=None, period_type='MONTHLY'):
        """
        Calculate performance for all active contractors.
        """
        if period_month is None or period_year is None:
            today = timezone.now().date()
            period_month = today.month
            period_year = today.year
        
        contractors = Contractor.objects.filter(is_active=True)
        results = []
        
        for contractor in contractors:
            try:
                metric = ContractorPerformanceService.calculate_contractor_performance(
                    contractor, period_month, period_year, period_type
                )
                results.append({
                    'contractor': contractor.contractor_name,
                    'score': metric.overall_performance_score,
                    'rating': metric.rating,
                    'risk_level': metric.risk_level
                })
            except Exception as e:
                print(f"Error calculating performance for {contractor.contractor_name}: {e}")
        
        return results
    
    @staticmethod
    def get_contractor_ranking(period_month=None, period_year=None):
        """
        Get ranking of all contractors by performance score.
        """
        if period_month is None or period_year is None:
            today = timezone.now().date()
            period_month = today.month
            period_year = today.year
        
        metrics = ContractorPerformanceMetric.objects.filter(
            period_month=period_month,
            period_year=period_year
        ).select_related('contractor').order_by('-overall_performance_score')
        
        ranking = []
        for idx, metric in enumerate(metrics, 1):
            ranking.append({
                'rank': idx,
                'id': metric.contractor.id,
                'contractor_name': metric.contractor.contractor_name,
                'contractor_code': metric.contractor.contractor_code,
                'score': metric.overall_performance_score,
                'rating': metric.rating,
                'risk_level': metric.risk_level,
                'inspections_count': metric.inspections_count,
                'work_orders_count': metric.work_orders_count
            })
        
        return ranking
    
    @staticmethod
    def get_contractor_performance_history(contractor_id, limit=12):
        """
        Get performance history for a specific contractor.
        """
        metrics = ContractorPerformanceMetric.objects.filter(
            contractor_id=contractor_id
        ).order_by('-period_year', '-period_month')[:limit]
        
        history = []
        for metric in metrics:
            history.append({
                'period': f"{metric.period_month}/{metric.period_year}",
                'period_type': metric.get_period_type_display(),
                'overall_score': metric.overall_performance_score,
                'rating': metric.rating,
                'inspection_score': metric.inspection_compliance_score,
                'training_score': metric.training_compliance_score,
                'onboarding_score': metric.document_compliance_score,  # Renamed for clarity
                'work_order_score': metric.work_order_completion_score,
                'inspections_count': metric.inspections_count,
                'work_orders_count': metric.work_orders_count
            })
        
        return history
    
    @staticmethod
    def get_performance_summary(period_month=None, period_year=None):
        """
        Get summary statistics for performance dashboard.
        """
        if period_month is None or period_year is None:
            today = timezone.now().date()
            period_month = today.month
            period_year = today.year
        
        metrics = ContractorPerformanceMetric.objects.filter(
            period_month=period_month,
            period_year=period_year
        ).select_related('contractor')
        
        total = metrics.count()
        
        if total == 0:
            return {
                'total_contractors': 0,
                'excellent_count': 0,
                'good_count': 0,
                'needs_improvement_count': 0,
                'poor_count': 0,
                'avg_score': 0,
                'max_score': 0,
                'min_score': 0
            }
        
        scores = [m.overall_performance_score for m in metrics]
        
        return {
            'total_contractors': total,
            'excellent_count': len([s for s in scores if s >= 90]),
            'good_count': len([s for s in scores if 75 <= s < 90]),
            'needs_improvement_count': len([s for s in scores if 60 <= s < 75]),
            'poor_count': len([s for s in scores if s < 60]),
            'avg_score': round(sum(scores) / len(scores), 1) if scores else 0,
            'max_score': max(scores) if scores else 0,
            'min_score': min(scores) if scores else 0
        }