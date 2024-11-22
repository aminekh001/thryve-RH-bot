# rhBot/signals.py

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Interview

@receiver(post_save, sender=Interview)
def handle_new_interview(sender, instance, created, **kwargs):
    if created:
        print(f"New interview created: {instance.interview_id}")
        # You can add additional logic here, such as:
        # - Sending a notification
        # - Updating related models
        # - Triggering an external API call

@receiver(pre_delete, sender=Interview)
def handle_interview_deletion(sender, instance, **kwargs):
    print(f"Interview being deleted: {instance.interview_id}")
    # You can add cleanup logic here, such as:
    # - Deleting related data
    # - Logging the deletion
    # - Notifying relevant parties

@receiver(post_save, sender=User)
def handle_new_user(sender, instance, created, **kwargs):
    if created:
        print(f"New user created: {instance.username}")
        # You can add user initialization logic here, such as:
        # - Creating a user profile
        # - Sending a welcome email
        # - Setting up default preferences

# Note: Remember to import and use these signals in your app's configuration
# This is typically done in the apps.py file, in the ready() method of your AppConfig