from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_add_question_hierarchy'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentanswer',
            name='time_spent_seconds',
            field=models.IntegerField(blank=True, help_text='Time spent on this question in seconds', null=True),
        ),
    ]
