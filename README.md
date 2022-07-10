
# mercurial-hacknplan
Mercurial hook that posts to HacknPlan tasks

Copy it to the `.hg` directory of your repository on the server, change its `hgrc` like this:

```ini
# .hg/hgrc
[hooks]
incoming.hacknplan-mentioned-issues = python:.hg/hooks.py:ReportToHacknPlan
```

and put a `HacknPlan_Settings.json` file right next to it:

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


#### Test

```zsh
mkdir hg_test_server
cd hg_test_server
hg init

cat <<EOS
[hooks]
incoming.hacknplan-mentioned-issues = python: ../hooks.py:ReportToHacknPlan
EOS >> .hg/hgrc

hg serve &


cd ..
hg clone http://localhost:8000 test_hg_cloned

cd test_hg_cloned
# DANGEROUS CONFIG - ONLY FOR LOCAL TESTING!
tee -a .hg/hgrc <<EOS
[web]
push_ssl=False
allow_push=*
EOS


echo 'Test file' > test.file.txt
hg add test.file.txt
hg commit -m 'test file added for testing purposes'
```