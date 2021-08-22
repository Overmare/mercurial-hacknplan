
# mercurial-hacknplan
Mercurial hook that posts to HacknPlan tasks

Copy it to the .hg directory of your repository on the server, change its hgrc like this:
```
[hooks]
incoming = python:.hg/hooks.py:ReportToHacknPlan
```
and put a HacknPlan_Settings.json file right next to it:
```
{
    "projectId": "123456",
    "apiKey": "ad9647c700c5454ba315360797ec0510",
    "commentHeader": "![Logo](https://www.mercurial-scm.org/hg-logo/droplets-24.png) Task related commits \\n\\n | | | \\n |:-|:-|:-| \\n",
    "commitTableRowFormat": "| [%s](https://project.local/hg/reponame/rev/%s) | %s | %s |\\n"
}
```

The hook also caches the name of the user from whom the api key was taken in order to track comments that have already been sent to change them. Information about this is stored in HacknPlan_HookCache.json
#
## Manual


If you want to associate a commit with a task, write its number after a hash in the commit description, multiple linking is supported

Example commit description : 
```
 #1 #2 #3 | I'm do something there, and there
```
or
```
 #47 #66  I'm do something there, and there
```
