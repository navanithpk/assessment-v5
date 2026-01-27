# Generated migration for two-step non-MCQ question system

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_answerspace_studentanswerspace_questionpage'),
    ]

    operations = [
        migrations.AddField(
            model_name='question',
            name='parts_config',
            field=models.JSONField(
                blank=True,
                null=True,
                help_text='JSON configuration for question parts (answer types, markschemes, etc.)'
            ),
        ),
        migrations.AddField(
            model_name='studentanswer',
            name='answer_parts',
            field=models.JSONField(
                blank=True,
                null=True,
                help_text='JSON structure storing answers for each question part'
            ),
        ),
    ]
