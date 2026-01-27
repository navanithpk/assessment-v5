from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class School(models.Model):
    """
    School model - Teachers and Students belong to a school
    """
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)  # e.g., "SCH001"
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["name"]
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class UserProfile(models.Model):
    """
    Extended user profile for role management
    """
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('school_admin', 'School Admin'),
    ]
    subject = models.CharField(max_length=100, blank=True, null=True)
    grade = models.IntegerField(null=True, blank=True)  # For students
    division = models.CharField(max_length=10, blank=True, null=True) 
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='users', null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["user__username"]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()} at {self.school}"


class Grade(models.Model):
    name = models.CharField(max_length=50)

    class Meta:
        ordering = ["name"]
        verbose_name = "Grade"
        verbose_name_plural = "Grades"

    def __str__(self):
        return self.name
        
        
class Subject(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
        
        
class Topic(models.Model):
    name = models.CharField(max_length=150)

    grade = models.ForeignKey(
        Grade,
        on_delete=models.CASCADE,
        related_name="topics"
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="topics"
    )

    class Meta:
        unique_together = ("name", "grade", "subject")
        ordering = ["grade__name", "subject__name", "name"]

    def __str__(self):
        return f"{self.grade} | {self.subject} | {self.name}"


class LearningObjective(models.Model):
    code = models.CharField(max_length=30)
    description = models.TextField()

    grade = models.ForeignKey(
        Grade,
        on_delete=models.CASCADE,
        related_name="learning_objectives"
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="learning_objectives"
    )

    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name="learning_objectives"
    )

    class Meta:
        unique_together = (
            "grade",
            "subject",
            "topic",
            "code",
        )
        ordering = ["grade__name", "subject__name", "topic__name", "code"]

    def __str__(self):
        return f"{self.grade}.{self.subject}.{self.topic}.{self.code}"


class Question(models.Model):

    QUESTION_TYPES = [
        ("mcq", "MCQ"),
        ("theory", "Theory"),
        ("structured", "Structured"),
        ("practical", "Practical"),
    ]

    grade = models.ForeignKey(Grade, on_delete=models.PROTECT)
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT)
    topic = models.ForeignKey(Topic, on_delete=models.PROTECT)
    year = models.PositiveIntegerField(null=True, blank=True)

    learning_objectives = models.ManyToManyField(
        LearningObjective,
        related_name="questions",
        blank=True
    )

    question_text = models.TextField()
    answer_text = models.TextField(blank=True)

    marks = models.PositiveIntegerField(default=1)
    question_type = models.CharField(
        max_length=20,
        choices=QUESTION_TYPES
    )

    # NEW: JSON configuration for question parts (Step 2 of two-step import)
    parts_config = models.JSONField(
        blank=True,
        null=True,
        help_text='JSON configuration for question parts (answer types, markschemes, etc.)'
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="questions"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Q{self.id} | {self.grade}.{self.subject}.{self.topic}"


# Update your Test model in models.py to add this field:

class Test(models.Model):
    title = models.CharField(max_length=255)
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    is_published = models.BooleanField(default=False)

    start_time = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    questions = models.ManyToManyField(
        "Question",
        through="TestQuestion",
        blank=True,
        related_name="tests"
    )
    
    assigned_students = models.ManyToManyField(
        "Student",
        blank=True,
        related_name="assigned_tests"
    )

    assigned_groups = models.ManyToManyField(
        "ClassGroup",
        blank=True,
        related_name="assigned_tests"
    )

    excluded_students = models.ManyToManyField(
        "Student",
        blank=True,
        related_name="excluded_from_tests"
    )
    
    # NEW FIELD for descriptive tests
    descriptive_structure = models.TextField(
        blank=True,
        null=True,
        help_text="JSON structure for descriptive/hierarchical questions"
    )
    
    test_type = models.CharField(
        max_length=20,
        choices=[
            ('standard', 'Standard Question Bank'),
            ('descriptive', 'Descriptive/Hierarchical')
        ],
        default='standard'
    )
    
    def __str__(self):
        return self.title
    
    def get_all_assigned_students(self):
        """
        Get all students assigned to this test (both directly and through groups)
        excluding those in excluded_students
        """
        from django.db.models import Q

        # Direct assignments
        direct_students = self.assigned_students.all()

        # Group assignments - get User IDs from groups, then find Students with those Users
        group_user_ids = []
        for group in self.assigned_groups.all():
            group_user_ids.extend(group.students.values_list('id', flat=True))

        group_students = Student.objects.filter(user_id__in=group_user_ids)

        # Combine and exclude
        all_students = (direct_students | group_students).distinct()
        excluded = self.excluded_students.all()

        return all_students.exclude(id__in=excluded)


# After adding this field, run migrations:
# python manage.py makemigrations
# python manage.py migrate


class TestQuestion(models.Model):
    test = models.ForeignKey(
        Test,
        on_delete=models.CASCADE,
        related_name="test_questions"
    )

    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE
    )

    order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.test.title} – Q{self.order}"


class Student(models.Model):
    full_name = models.CharField(max_length=200)
    roll_number = models.CharField(max_length=50, blank=True)
    admission_id = models.CharField(max_length=50, blank=True)

    grade = models.ForeignKey(Grade, on_delete=models.CASCADE)
    section = models.CharField(max_length=10)  # A, B, C
    school = models.ForeignKey(School, on_delete=models.CASCADE, null=True, blank=True)
    
    # Link Student to User account
    user = models.OneToOneField(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='student_profile'
    )
    
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='students_created')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("grade", "section", "roll_number", "school")
        ordering = ["school", "grade", "section", "roll_number"]

    def __str__(self):
        return f"{self.full_name} ({self.grade}-{self.section})"


class ClassGroup(models.Model):
    name = models.CharField(max_length=200)
    school = models.ForeignKey('School', on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    grade = models.ForeignKey('Grade', on_delete=models.SET_NULL, null=True, blank=True)
    students = models.ManyToManyField(User, related_name='student_groups', blank=True)
    
    section = models.CharField(max_length=10, blank=True)  # e.g., "A", "B", "Morning"
    subject = models.ForeignKey('Subject', on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return self.name


class StudentAnswer(models.Model):
    """
    Stores student answers/attempts for test questions
    """
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="answers"
    )
    
    test = models.ForeignKey(
        Test,
        on_delete=models.CASCADE,
        related_name="student_answers"
    )
    
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE
    )
    
    answer_text = models.TextField(blank=True)

    # NEW: JSON structure for multi-part question answers
    answer_parts = models.JSONField(
        blank=True,
        null=True,
        help_text='JSON structure storing answers for each question part'
    )

    marks_awarded = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    submitted_at = models.DateTimeField(auto_now_add=True)
    evaluated_at = models.DateTimeField(null=True, blank=True)
    evaluated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="evaluated_answers"
    )
    
    class Meta:
        unique_together = ("student", "test", "question")
        ordering = ["test", "student", "question"]
    
    def __str__(self):
        return f"{self.student.full_name} - {self.test.title} - Q{self.question.id}"


class PDFImportSession(models.Model):
    """
    Tracks PDF import sessions for resuming later
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('paused', 'Paused'),
    ]

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='import_sessions')
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    year = models.IntegerField()

    # Session metadata
    session_name = models.CharField(max_length=200)
    total_files = models.IntegerField(default=0)
    processed_files = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Store file information as JSON
    # Format: [{"qp_name": "...", "ms_name": "...", "processed": true/false, "question_ids": [...]}, ...]
    files_data = models.JSONField(default=list)

    # Store slicing configuration for each file
    # Format: {"file_index": {"linesByPage": {...}, "settings": {...}}, ...}
    slicing_data = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.session_name} - {self.processed_files}/{self.total_files} files"

    @property
    def progress_percentage(self):
        if self.total_files == 0:
            return 0
        return int((self.processed_files / self.total_files) * 100)


class ProcessedPDF(models.Model):
    """
    Tracks processed PDF files to prevent duplicate processing
    """
    file_name = models.CharField(max_length=500)
    file_hash = models.CharField(max_length=64, unique=True)  # SHA-256 hash
    processed_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='processed_pdfs')
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    year = models.IntegerField(null=True, blank=True)

    questions_created = models.IntegerField(default=0)
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-processed_at']

    def __str__(self):
        return f"{self.file_name} ({self.processed_at.date()})"


class AnswerSpace(models.Model):
    """
    Defines an answer space on a structured question
    For prototype: Focus on text_line type
    """
    SPACE_TYPES = [
        ('text_line', 'Text Line (1-2 lines)'),
        ('calc_space', 'Calculation Space'),
        ('table_cell', 'Table Cell'),
        ('canvas', 'Drawing Canvas'),
    ]

    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answer_spaces')
    space_type = models.CharField(max_length=20, choices=SPACE_TYPES, default='text_line')

    # Position on question image (pixels from top-left)
    x = models.IntegerField(default=0)
    y = models.IntegerField(default=0)
    width = models.IntegerField(default=600)
    height = models.IntegerField(default=80)

    # Configuration stored as JSON
    # For text_line: {"lines": 2, "max_chars": 200, "placeholder": "Type your answer..."}
    # For calc_space: {"unit": "m/s", "show_grid": true}
    # For table_cell: {"row": 2, "col": 3, "table_id": "table1"}
    # For canvas: {"grid": true, "tools": ["pen", "line", "shape"]}
    config = models.JSONField(default=dict, blank=True)

    # Ordering for display
    order = models.IntegerField(default=0)

    # Marks allocated to this answer space
    marks = models.DecimalField(max_digits=5, decimal_places=2, default=1)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['question', 'order']

    def __str__(self):
        return f"{self.question.id} - {self.get_space_type_display()} (Order: {self.order})"


class StudentAnswerSpace(models.Model):
    """
    Student's response to an answer space
    Stores both the input and rasterized version
    """
    student_answer = models.ForeignKey(
        StudentAnswer,
        on_delete=models.CASCADE,
        related_name='space_responses'
    )
    answer_space = models.ForeignKey(AnswerSpace, on_delete=models.CASCADE)

    # Text response (HTML from rich text editor)
    text_response = models.TextField(blank=True)

    # Canvas data (base64 PNG for drawings)
    canvas_data = models.TextField(blank=True)

    # Rasterized image overlay (PNG base64)
    # This is the final rendered version placed on question image
    rasterized_image = models.TextField(blank=True)

    # OCR extracted text (for grading assistance)
    ocr_text = models.TextField(blank=True)

    # Grading
    marks_awarded = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    feedback = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['student_answer', 'answer_space']

    def __str__(self):
        return f"Response: {self.student_answer.student.user.username} - Space {self.answer_space.id}"


class QuestionPage(models.Model):
    """
    Tracks multi-page questions during structured paper import
    Multiple pages can belong to one question
    """
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='pages')
    page_number = models.IntegerField()  # Sequential order (1, 2, 3, ...)

    # Page image data (base64 encoded PNG)
    page_image = models.TextField()

    # Boundary markers
    has_green_line = models.BooleanField(default=False)  # Start of question
    has_red_line = models.BooleanField(default=False)    # End of question

    # Blue rectangle bounds (defines question width)
    blue_rect_x = models.IntegerField(null=True, blank=True)
    blue_rect_y = models.IntegerField(null=True, blank=True)
    blue_rect_width = models.IntegerField(null=True, blank=True)
    blue_rect_height = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['question', 'page_number']
        unique_together = ['question', 'page_number']

    def __str__(self):
        markers = []
        if self.has_green_line:
            markers.append('GREEN')
        if self.has_red_line:
            markers.append('RED')
        marker_str = f" [{', '.join(markers)}]" if markers else ""
        return f"Q{self.question.id} Page {self.page_number}{marker_str}"