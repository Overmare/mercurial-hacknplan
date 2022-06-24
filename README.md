
# mercurial-hacknplan
Mercurial hook that posts to HacknPlan tasks

Copy it to the .hg directory of your repository on the server, change its hgrc like this:

```ini
[hooks]
incoming.hacknplan-mentioned-issues = python:.hg/hooks.py:ReportToHacknPlan
```

and put a HacknPlan_Settings.json file right next to it:

```sh
cp HacknPlan_Settings.example.json HacknPlan_Settings.json
```

The hook also caches the name of the user from whom the api key was taken in order to track comments that have already been sent to change them. Information about this is stored in HacknPlan_HookCache.json
#
## Manual


If you want to associate a commit with a task, write it's number after a hash in the commit description, multiple linking is supported

Example commit description : 
```
 #1 #2 #3 | I'm do something there, and there
```
or
```
 #47 #66  I'm do something there, and there
```
