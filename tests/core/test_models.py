from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.test.testcases import TestCase
from django.urls import re_path
from wiki.conf import settings
from wiki.managers import ArticleManager
from wiki.models import Article
from wiki.models import ArticleRevision
from wiki.models import URLPath
from wiki.models.pluginbase import ReusablePlugin
from wiki.models.pluginbase import RevisionPlugin
from wiki.models.pluginbase import RevisionPluginRevision
from wiki.models.pluginbase import SimplePlugin
from wiki.urls import WikiURLPatterns

User = get_user_model()
Group = apps.get_model(settings.GROUP_MODEL)


class WikiCustomUrlPatterns(WikiURLPatterns):
    def get_article_urls(self):
        urlpatterns = [
            re_path(
                "^my-wiki/(?P<article_id>[0-9]+)/$",
                self.article_view_class.as_view(),
                name="get",
            ),
        ]
        return urlpatterns

    def get_article_path_urls(self):
        urlpatterns = [
            re_path(
                "^my-wiki/(?P<path>.+/|)$",
                self.article_view_class.as_view(),
                name="get",
            ),
        ]
        return urlpatterns


class ArticleModelTest(TestCase):
    def test_default_fields_of_empty_article(self):

        a = Article.objects.create()

        self.assertIsNone(a.current_revision)
        self.assertIsNone(a.owner)
        self.assertIsNone(a.group)

        self.assertIsNotNone(a.created)
        self.assertIsNotNone(a.modified)

        self.assertIsNotNone(a.group_read)
        self.assertIsNotNone(a.group_write)
        self.assertIsNotNone(a.other_read)
        self.assertIsNotNone(a.other_write)

    # XXX maybe redundant test
    def test_model_manager_class(self):

        self.assertIsInstance(Article.objects, ArticleManager)

    def test_str_method_if_have_current_revision(self):

        title = "Test title"

        a = Article.objects.create()
        ArticleRevision.objects.create(article=a, title=title)

        self.assertEqual(str(a), title)

    def test_str_method_if_dont_have_current_revision(self):

        a = Article.objects.create()

        expected = "Article without content (1)"

        self.assertEqual(str(a), expected)

    def test_get_absolute_url_if_urlpath_set_is_exists(self):

        a1 = Article.objects.create()
        s1 = Site.objects.create(domain="something.com", name="something.com")
        u1 = URLPath.objects.create(article=a1, site=s1)

        a2 = Article.objects.create()
        s2 = Site.objects.create(domain="somethingelse.com", name="somethingelse.com")
        URLPath.objects.create(article=a2, site=s2, parent=u1, slug="test_slug")

        url = a2.get_absolute_url()

        expected = "/test_slug/"

        self.assertEqual(url, expected)

    def test_get_absolute_url_if_urlpath_set_is_not_exists(self):

        a = Article.objects.create()

        url = a.get_absolute_url()

        expected = "/1/"

        self.assertEqual(url, expected)

    def test_article_is_related_to_articlerevision(self):

        title = "Test title"

        a = Article.objects.create()
        r = ArticleRevision.objects.create(article=a, title=title)

        self.assertEqual(r.article, a)
        self.assertIn(r, a.articlerevision_set.all())

    def test_article_is_related_to_owner(self):

        u = User.objects.create(username="Noman", password="pass")
        a = Article.objects.create(owner=u)

        self.assertEqual(a.owner, u)
        self.assertIn(a, u.owned_articles.all())

    def test_article_is_related_to_group(self):

        g = Group.objects.create()
        a = Article.objects.create(group=g)

        self.assertEqual(a.group, g)
        self.assertIn(a, g.article_set.all())

    def test_cache(self):
        a = Article.objects.create()
        ArticleRevision.objects.create(article=a, title="test", content="# header")
        expected = """<h1 id="wiki-toc-header">header""" """.*</h1>"""
        # cached content does not exist yet. this will create it
        self.assertRegexpMatches(a.get_cached_content(), expected)
        # actual cached content test
        self.assertRegexpMatches(a.get_cached_content(), expected)

    def test_articlerevision_relation_addrevision(self):
        a = Article.objects.create()

        r1 = ArticleRevision(title="revision1")
        a.add_revision(r1)

        r2 = ArticleRevision(title="revision2", article=a)
        r2.save()
        a.add_revision(r2)

        r3 = ArticleRevision(title="revision2")
        a.add_revision(r3)

        self.assertEqual(a.current_revision, r3)

        self.assertEqual(r1.revision_number, 1)
        self.assertEqual(r2.revision_number, 2)
        self.assertEqual(r3.revision_number, 3)

        self.assertIsNone(r1.previous_revision)
        self.assertEqual(r2.previous_revision, r1)
        self.assertEqual(r3.previous_revision, r2)

    def test_articlerevision_saving(self):
        a = Article.objects.create()

        r1 = ArticleRevision(article=a, title="revision3a")
        r1.save()
        r2 = ArticleRevision(article=a, title="revision3b")
        r2.save()

        self.assertEqual(a.current_revision, r1)

        self.assertEqual(r1.revision_number, 1)
        self.assertEqual(r2.revision_number, 2)

        self.assertIsNone(r1.previous_revision)
        self.assertEqual(r2.previous_revision, r1)


class PluginBaseModelTest(TestCase):
    def test_simple_plugin(self):

        a = Article.objects.create()
        ar = ArticleRevision.objects.create(article=a, title="test")

        p = SimplePlugin(article=a)
        p.save()

        self.assertIsNotNone(p.article_revision)
        self.assertNotEqual(p.article_revision, ar)
        self.assertEqual(p.article_revision, a.current_revision)
        self.assertEqual(p.article_revision.previous_revision, ar)

    def test_default_fields_plugins(self):
        a = Article.objects.create()
        r = RevisionPlugin.objects.create(article=a)

        self.assertIsNone(r.current_revision)

    def test_reusable_plugins_related(self):
        a1 = Article.objects.create()
        a2 = Article.objects.create()

        p = ReusablePlugin.objects.create(article=a1)
        pk = p.pk
        p.articles.add(a2)
        p.save()

        self.assertEqual(a1, p.article)
        self.assertNotIn(a1, p.articles.all())

        p.article = None
        p.save()  # <---- Raise a RelatedObjectDoesNotExist exception

        self.assertIsEqual(p.article, a2)

        a2.delete()
        with self.assertRaises(ReusablePlugin.DoesNotExist):
            ReusablePlugin.objects.get(pk=pk)

    def test_revision_plugin_revision_saving(self):
        a = Article.objects.create()
        p = RevisionPlugin.objects.create(article=a)

        r1 = RevisionPluginRevision(plugin=p)
        r1.save()
        r2 = RevisionPluginRevision(plugin=p)
        r2.save()

        self.assertEqual(r1, p.current_revision)

        self.assertEqual(r1.revision_number, 1)
        self.assertEqual(r2.revision_number, 2)

        self.assertIsNone(r1.previous_revision)
        self.assertEqual(r2.previous_revision, r1)

    def test_revision_plugin_revision_addrevision(self):
        a = Article.objects.create()
        p = RevisionPlugin.objects.create(article=a)

        r1 = RevisionPluginRevision()
        p.add_revision(r1)
        r2 = RevisionPluginRevision(plugin=p)
        r2.save()
        p.add_revision(r2)
        r3 = RevisionPluginRevision()
        p.add_revision(r3)

        self.assertEqual(r3, p.current_revision)

        self.assertEqual(r1.revision_number, 1)
        self.assertEqual(r2.revision_number, 2)
        self.assertEqual(r3.revision_number, 3)

        self.assertEqual(r1.plugin, p)

        self.assertIsNone(r1.previous_revision)
        self.assertEqual(r2.previous_revision, r1)
        self.assertEqual(r3.previous_revision, r2)
