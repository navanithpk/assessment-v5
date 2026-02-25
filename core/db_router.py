"""
Database Router for Multi-Database Question Bank Architecture

Each QuestionBank DLC gets its own SQLite database file.
For example:
- 9702_physics.db for AS & A Level Physics
- 0625_physics.db for IGCSE Physics
- jee_physics.db for JEE Physics
"""


class QuestionBankRouter:
    """
    A router to control database operations for Question-related models
    based on their associated QuestionBank.
    """

    question_models = {'Question', 'TestQuestion', 'StudentAnswer'}

    def db_for_read(self, model, **hints):
        """
        Route read operations for Question models to their QuestionBank database
        """
        if model.__name__ in self.question_models:
            # Check if there's a QuestionBank hint
            question_bank = hints.get('question_bank')
            if question_bank and question_bank.database_file:
                return self._get_db_alias(question_bank)

        # Default to main database
        return None

    def db_for_write(self, model, **hints):
        """
        Route write operations for Question models to their QuestionBank database
        """
        if model.__name__ in self.question_models:
            question_bank = hints.get('question_bank')
            if question_bank and question_bank.database_file:
                return self._get_db_alias(question_bank)

        # Default to main database
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if both objects are in the same database
        """
        # Allow all relations within the main database
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Control which models get migrated to which database
        """
        # Question models should migrate to their specific databases
        if model_name in ['question', 'testquestion', 'studentanswer']:
            # Only migrate to main DB if no specific DB is being targeted
            return db == 'default'

        # All other models only in default database
        return db == 'default'

    def _get_db_alias(self, question_bank):
        """
        Generate a database alias from QuestionBank
        Format: qb_<code>  (e.g., qb_9702, qb_0625)
        """
        if question_bank.subject and question_bank.subject.code:
            return f"qb_{question_bank.subject.code}"
        return f"qb_{question_bank.id}"
