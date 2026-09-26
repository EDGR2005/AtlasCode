"""Django ORM models for the sample-db-project fixture."""
from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        db_table = "categories"


class Article(models.Model):
    title = models.CharField(max_length=255)
    body = models.TextField(null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    author_id = models.IntegerField()
    published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "articles"


class ArticleTag(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    tag_name = models.CharField(max_length=64)

    class Meta:
        db_table = "article_tags"
