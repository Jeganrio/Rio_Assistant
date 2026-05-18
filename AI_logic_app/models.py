from django.db import models

# Create your models here.
class CubyQueries(models.Model):
    query = models.TextField()
    answers = models.TextField(blank = True, null = True)

def save_data_in_db(query, answers):
    obj = CubyQueries(query = query, answers = answers)
    obj.save()
