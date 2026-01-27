"""
Analytics Engine for Lumen Assessment Platform
Provides comprehensive performance metrics for students and teachers
"""
from django.db.models import Avg, Count, StdDev, Max, Min, Q, F
from django.utils import timezone
from datetime import timedelta, datetime
from collections import defaultdict
import statistics
from .models import StudentAnswer, Test, Question, Student, Topic, LearningObjective, Subject


class StudentAnalytics:
    """Individual student performance analytics"""

    def __init__(self, student, start_date=None, end_date=None):
        self.student = student
        self.start_date = start_date or (timezone.now() - timedelta(days=365))
        self.end_date = end_date or timezone.now()

    def _get_answers_in_range(self):
        """Get all graded answers in the date range"""
        return StudentAnswer.objects.filter(
            student=self.student,
            marks_awarded__isnull=False,
            test__is_published=True,
            submitted_at__gte=self.start_date,
            submitted_at__lte=self.end_date
        ).select_related('question', 'test', 'question__topic', 'question__subject')

    # ==================== SUBJECT-LEVEL PERFORMANCE ====================

    def subject_performance_summary(self):
        """
        Performance across different subjects
        Returns: List of dicts with subject metrics
        """
        answers = self._get_answers_in_range()
        subject_data = defaultdict(lambda: {'scores': [], 'total_marks': 0, 'earned_marks': 0})

        for ans in answers:
            subject = ans.question.subject.name
            percentage = (float(ans.marks_awarded) / float(ans.question.marks)) * 100 if ans.question.marks > 0 else 0
            subject_data[subject]['scores'].append(percentage)
            subject_data[subject]['total_marks'] += float(ans.question.marks)
            subject_data[subject]['earned_marks'] += float(ans.marks_awarded)

        results = []
        for subject, data in subject_data.items():
            avg_percentage = sum(data['scores']) / len(data['scores']) if data['scores'] else 0
            consistency = statistics.stdev(data['scores']) if len(data['scores']) > 1 else 0

            results.append({
                'subject': subject,
                'avg_percentage': round(avg_percentage, 2),
                'consistency': round(consistency, 2),  # Lower is better
                'total_questions': len(data['scores']),
                'overall_percentage': round((data['earned_marks'] / data['total_marks'] * 100) if data['total_marks'] > 0 else 0, 2)
            })

        # Sort by average percentage descending
        results.sort(key=lambda x: x['avg_percentage'], reverse=True)

        # Add rank
        for idx, item in enumerate(results, 1):
            item['rank'] = idx

        return results

    def subject_performance_trend(self, subject):
        """
        Performance trend for a specific subject over time
        Returns: Time-series data with trend analysis
        """
        answers = self._get_answers_in_range().filter(question__subject__name=subject).order_by('submitted_at')

        if not answers.exists():
            return None

        # Group by test
        test_scores = defaultdict(list)
        test_dates = {}

        for ans in answers:
            test_id = ans.test.id
            percentage = (float(ans.marks_awarded) / float(ans.question.marks)) * 100 if ans.question.marks > 0 else 0
            test_scores[test_id].append(percentage)
            test_dates[test_id] = ans.submitted_at

        # Calculate average per test
        time_series = []
        for test_id, scores in test_scores.items():
            time_series.append({
                'date': test_dates[test_id],
                'score': round(sum(scores) / len(scores), 2),
                'test_id': test_id
            })

        time_series.sort(key=lambda x: x['date'])

        # Calculate trend (linear regression slope)
        if len(time_series) >= 2:
            scores = [item['score'] for item in time_series]
            n = len(scores)
            x_vals = list(range(n))

            # Simple linear regression
            x_mean = sum(x_vals) / n
            y_mean = sum(scores) / n

            numerator = sum((x_vals[i] - x_mean) * (scores[i] - y_mean) for i in range(n))
            denominator = sum((x_vals[i] - x_mean) ** 2 for i in range(n))

            slope = numerator / denominator if denominator != 0 else 0

            # Classify trend
            if slope > 2:
                trend = 'improving'
            elif slope < -2:
                trend = 'declining'
            else:
                trend = 'stable'
        else:
            slope = 0
            trend = 'insufficient_data'

        # Rolling average (window of 3)
        rolling_avg = []
        for i in range(len(time_series)):
            start_idx = max(0, i - 2)
            window = time_series[start_idx:i + 1]
            avg = sum(item['score'] for item in window) / len(window)
            rolling_avg.append(round(avg, 2))

        # Best and worst
        scores_only = [item['score'] for item in time_series]
        best_score = max(scores_only) if scores_only else 0
        worst_score = min(scores_only) if scores_only else 0

        # Variance
        variance = statistics.variance(scores_only) if len(scores_only) > 1 else 0

        return {
            'time_series': time_series,
            'rolling_avg': rolling_avg,
            'trend': trend,
            'slope': round(slope, 3),
            'best_score': best_score,
            'worst_score': worst_score,
            'stability_index': round(variance, 2)
        }

    # ==================== TOPIC & LO LEVEL PERFORMANCE ====================

    def topic_performance(self):
        """Performance across specific topics"""
        answers = self._get_answers_in_range()
        topic_data = defaultdict(lambda: {'correct': 0, 'total': 0, 'scores': []})

        for ans in answers:
            if ans.question.topic:
                topic_name = ans.question.topic.name
                percentage = (float(ans.marks_awarded) / float(ans.question.marks)) * 100 if ans.question.marks > 0 else 0
                topic_data[topic_name]['scores'].append(percentage)
                topic_data[topic_name]['total'] += 1
                if percentage >= 60:  # Consider 60% as mastery threshold
                    topic_data[topic_name]['correct'] += 1

        results = []
        for topic, data in topic_data.items():
            mastery_percentage = (data['correct'] / data['total'] * 100) if data['total'] > 0 else 0
            avg_score = sum(data['scores']) / len(data['scores']) if data['scores'] else 0

            # Classify strength
            if mastery_percentage >= 80:
                classification = 'strong'
            elif mastery_percentage >= 50:
                classification = 'moderate'
            else:
                classification = 'weak'

            results.append({
                'topic': topic,
                'mastery_percentage': round(mastery_percentage, 2),
                'avg_score': round(avg_score, 2),
                'questions_attempted': data['total'],
                'classification': classification
            })

        results.sort(key=lambda x: x['mastery_percentage'], reverse=True)
        return results

    def lo_performance(self):
        """Performance per Learning Objective"""
        answers = self._get_answers_in_range()
        lo_data = defaultdict(lambda: {'correct': 0, 'total': 0, 'scores': [], 'attempts': []})

        for ans in answers:
            for lo in ans.question.learning_objectives.all():
                lo_key = f"{lo.code}: {lo.description[:50]}"
                percentage = (float(ans.marks_awarded) / float(ans.question.marks)) * 100 if ans.question.marks > 0 else 0

                lo_data[lo_key]['scores'].append(percentage)
                lo_data[lo_key]['attempts'].append(ans.submitted_at)
                lo_data[lo_key]['total'] += 1
                if percentage >= 60:
                    lo_data[lo_key]['correct'] += 1

        results = []
        for lo, data in lo_data.items():
            mastery_percentage = (data['correct'] / data['total'] * 100) if data['total'] > 0 else 0

            # Calculate improvement rate (comparing first half to second half)
            scores = data['scores']
            if len(scores) >= 4:
                mid = len(scores) // 2
                first_half_avg = sum(scores[:mid]) / mid
                second_half_avg = sum(scores[mid:]) / (len(scores) - mid)
                improvement_rate = second_half_avg - first_half_avg
            else:
                improvement_rate = 0

            # Volatility (standard deviation)
            volatility = statistics.stdev(scores) if len(scores) > 1 else 0

            results.append({
                'lo': lo,
                'mastery_percentage': round(mastery_percentage, 2),
                'attempt_frequency': data['total'],
                'improvement_rate': round(improvement_rate, 2),
                'volatility': round(volatility, 2)
            })

        results.sort(key=lambda x: x['mastery_percentage'], reverse=True)
        return results

    # ==================== ASSESSMENT-LEVEL PERFORMANCE ====================

    def test_performance(self, test_id):
        """Performance analytics for one particular test"""
        test = Test.objects.get(id=test_id)
        answers = StudentAnswer.objects.filter(
            student=self.student,
            test=test,
            marks_awarded__isnull=False
        ).select_related('question', 'question__topic')

        if not answers.exists():
            return None

        # Calculate totals
        total_marks = sum(float(ans.question.marks) for ans in answers)
        earned_marks = sum(float(ans.marks_awarded) for ans in answers)
        percentage = (earned_marks / total_marks * 100) if total_marks > 0 else 0

        # Topic-wise breakdown
        topic_breakdown = defaultdict(lambda: {'total': 0, 'earned': 0})
        for ans in answers:
            if ans.question.topic:
                topic = ans.question.topic.name
                topic_breakdown[topic]['total'] += float(ans.question.marks)
                topic_breakdown[topic]['earned'] += float(ans.marks_awarded)

        topic_results = []
        for topic, data in topic_breakdown.items():
            topic_results.append({
                'topic': topic,
                'percentage': round((data['earned'] / data['total'] * 100) if data['total'] > 0 else 0, 2),
                'marks': f"{data['earned']}/{data['total']}"
            })

        # LO-wise breakdown
        lo_breakdown = defaultdict(lambda: {'total': 0, 'earned': 0})
        for ans in answers:
            for lo in ans.question.learning_objectives.all():
                lo_key = f"{lo.code}: {lo.description[:50]}"
                lo_breakdown[lo_key]['total'] += float(ans.question.marks)
                lo_breakdown[lo_key]['earned'] += float(ans.marks_awarded)

        lo_results = []
        for lo, data in lo_breakdown.items():
            lo_results.append({
                'lo': lo,
                'percentage': round((data['earned'] / data['total'] * 100) if data['total'] > 0 else 0, 2),
                'marks': f"{data['earned']}/{data['total']}"
            })

        # Class percentile (if we have other students' data)
        class_scores = StudentAnswer.objects.filter(
            test=test,
            marks_awarded__isnull=False
        ).values('student').annotate(
            total_earned=Sum('marks_awarded')
        )

        if class_scores.count() > 1:
            student_scores = [float(score['total_earned']) for score in class_scores]
            student_scores.sort()
            student_rank = sum(1 for score in student_scores if score <= earned_marks)
            percentile = (student_rank / len(student_scores)) * 100
        else:
            percentile = None

        return {
            'test': test,
            'total_marks': total_marks,
            'earned_marks': earned_marks,
            'percentage': round(percentage, 2),
            'percentile': round(percentile, 2) if percentile else None,
            'topic_breakdown': topic_results,
            'lo_breakdown': lo_results
        }

    # ==================== COMPARATIVE & DIAGNOSTIC ====================

    def strengths_and_weaknesses(self):
        """Identify strong and weak LOs"""
        lo_perf = self.lo_performance()

        strong_los = [lo for lo in lo_perf if lo['mastery_percentage'] >= 80]
        weak_los = [lo for lo in lo_perf if lo['mastery_percentage'] < 50]

        # Persistent weak LOs (attempted 3+ times, still weak)
        persistent_weak = [lo for lo in weak_los if lo['attempt_frequency'] >= 3]

        return {
            'strong': strong_los[:10],  # Top 10
            'weak': weak_los[:10],  # Bottom 10
            'persistent_weak': persistent_weak
        }

    def engagement_metrics(self):
        """Engagement and coverage metrics"""
        answers = self._get_answers_in_range()

        # Total LOs in curriculum for this student's grade
        total_los = LearningObjective.objects.filter(
            grade=self.student.grade
        ).count()

        # LOs attempted
        attempted_los = set()
        for ans in answers:
            for lo in ans.question.learning_objectives.all():
                attempted_los.add(lo.id)

        lo_coverage = (len(attempted_los) / total_los * 100) if total_los > 0 else 0

        # Topics attempted
        topics_attempted = set(ans.question.topic.id for ans in answers if ans.question.topic)
        total_topics = Topic.objects.filter(
            grade=self.student.grade
        ).count()

        topic_coverage = (len(topics_attempted) / total_topics * 100) if total_topics > 0 else 0

        # Attempt rate (answers per week)
        days_in_range = (self.end_date - self.start_date).days
        weeks = days_in_range / 7 if days_in_range > 0 else 1
        attempt_rate = answers.count() / weeks

        return {
            'lo_coverage_percentage': round(lo_coverage, 2),
            'topic_coverage_percentage': round(topic_coverage, 2),
            'attempt_rate_per_week': round(attempt_rate, 2),
            'total_questions_attempted': answers.count()
        }


class ClassAnalytics:
    """Group/Class/Cohort performance analytics"""

    def __init__(self, school, grade=None, section=None, class_group=None, start_date=None, end_date=None):
        self.school = school
        self.grade = grade
        self.section = section
        self.class_group = class_group
        self.start_date = start_date or (timezone.now() - timedelta(days=365))
        self.end_date = end_date or timezone.now()

    def _get_students(self):
        """Get students in this class"""
        query = Student.objects.filter(school=self.school)

        if self.grade:
            query = query.filter(grade=self.grade)
        if self.section:
            query = query.filter(section=self.section)
        if self.class_group:
            # Get user IDs from class group
            user_ids = self.class_group.students.values_list('id', flat=True)
            query = query.filter(user_id__in=user_ids)

        return query

    def class_average_per_subject(self):
        """Class average performance per subject"""
        students = self._get_students()

        answers = StudentAnswer.objects.filter(
            student__in=students,
            marks_awarded__isnull=False,
            test__is_published=True,
            submitted_at__gte=self.start_date,
            submitted_at__lte=self.end_date
        ).select_related('question', 'question__subject')

        subject_data = defaultdict(lambda: {'scores': []})

        for ans in answers:
            subject = ans.question.subject.name
            percentage = (float(ans.marks_awarded) / float(ans.question.marks)) * 100 if ans.question.marks > 0 else 0
            subject_data[subject]['scores'].append(percentage)

        results = []
        for subject, data in subject_data.items():
            scores = data['scores']
            results.append({
                'subject': subject,
                'mean': round(statistics.mean(scores), 2) if scores else 0,
                'median': round(statistics.median(scores), 2) if scores else 0,
                'std_dev': round(statistics.stdev(scores), 2) if len(scores) > 1 else 0,
                'count': len(scores)
            })

        return results

    def lo_mastery_heatmap(self):
        """LO mastery across the class"""
        students = self._get_students()

        answers = StudentAnswer.objects.filter(
            student__in=students,
            marks_awarded__isnull=False,
            test__is_published=True,
            submitted_at__gte=self.start_date,
            submitted_at__lte=self.end_date
        ).select_related('question')

        lo_data = defaultdict(lambda: {'mastered': 0, 'total_students': set()})

        for ans in answers:
            for lo in ans.question.learning_objectives.all():
                lo_key = f"{lo.code}: {lo.description[:50]}"
                percentage = (float(ans.marks_awarded) / float(ans.question.marks)) * 100 if ans.question.marks > 0 else 0

                lo_data[lo_key]['total_students'].add(ans.student.id)
                if percentage >= 60:
                    lo_data[lo_key]['mastered'] += 1

        results = []
        for lo, data in lo_data.items():
            student_count = len(data['total_students'])
            mastery_percentage = (data['mastered'] / student_count * 100) if student_count > 0 else 0

            # Red zone if < 50% mastery
            is_red_zone = mastery_percentage < 50

            results.append({
                'lo': lo,
                'mastery_percentage': round(mastery_percentage, 2),
                'students_mastered': data['mastered'],
                'total_students': student_count,
                'is_red_zone': is_red_zone
            })

        results.sort(key=lambda x: x['mastery_percentage'])
        return results

    def at_risk_students(self, threshold=40):
        """Identify at-risk students"""
        students = self._get_students()
        at_risk = []

        for student in students:
            analytics = StudentAnalytics(student, self.start_date, self.end_date)
            subject_perf = analytics.subject_performance_summary()

            if subject_perf:
                overall_avg = sum(s['avg_percentage'] for s in subject_perf) / len(subject_perf)

                if overall_avg < threshold:
                    at_risk.append({
                        'student': student,
                        'average': round(overall_avg, 2),
                        'status': 'at_risk'
                    })

        return at_risk


# Utility import for Sum
from django.db.models import Sum
