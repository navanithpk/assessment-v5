from .models import Student, StudentAnswer


def student_results_available(request):
    """
    Context processor to check if the logged-in student has any graded results.
    This is used to conditionally enable the "My Results" navigation link.
    """
    has_results = False

    if request.user.is_authenticated:
        try:
            student = Student.objects.get(user=request.user)
            # Check if there are any student answers with awarded marks
            has_results = StudentAnswer.objects.filter(
                student=student,
                marks_awarded__isnull=False
            ).exists()
        except Student.DoesNotExist:
            pass

    return {
        'has_graded_results': has_results
    }
