import json
import os
import re
import urllib
from mercurial.ui import ui

hookDirectory = os.path.dirname(os.path.abspath(__file__))
cacheFilePath = hookDirectory + "/HacknPlan_HookCache.json"
secretsFilePath = hookDirectory + "/HacknPlan_Settings.json"

TASK_REGEX = re.compile(r'(?:\W|^)#(?P<issue>\d+)\b')


def PrintErrorMsg(ui, msg):
    ui.write((msg + "\n").encode("utf-8"))
# end def


try:
    secrets = json.load(open(secretsFilePath))
except (IOError, ValueError) as ex:
    PrintErrorMsg(
        ui,
        "Hack-n-Plan incoming hook could not load secrets because %s \nand.. stopped execution ¯\_(ツ)_/¯" % str(ex)
    )
    exit(1)
# end try

apiKey = secrets['apiKey']
projectId = secrets['projectId']
commentHeader = secrets['commentHeader']
commitTableRowFormat = secrets['commitTableRowFormat']


def ReportToHacknPlan(ui, repo, node, **kwargs):
    hookUserName = GetHookUserName()
    commitInfo = repo[node]

    rawCommitDescription = commitInfo.description().decode("utf-8")
    taskIds = ParseTaskIds(rawCommitDescription)

    if len(taskIds) == 0:
        return

    commitUser = commitInfo.user().decode("utf-8")
    commitHash = commitInfo.hex()[:12].decode("utf-8")
    commitDescription = FormatCommitMessage(commitHash, commitUser, rawCommitDescription)

    for taskId in taskIds:
        comments = GetCommentsItemsForTask(taskId)
        existingComment = GetCommentItemForEdit(comments, hookUserName)
        if existingComment != None:
            EditOldComment(existingComment, commitDescription)
        else:
            SendNewComment(taskId, commitDescription)


########################
#   Main Actions
########################

def EditOldComment(inCommentItem, inCommitMessages):
    taskId = inCommentItem['workItemId']
    commentId = inCommentItem['commentId']
    commentTextForSend = inCommentItem['text'] + ''.join(inCommitMessages)
    url = 'https://api.hacknplan.com/v0/projects/{project}/workitems/{task}/comments/{comment}'.format(
        project=projectId, task=taskId, comment=commentId
    )
    urlRequest = CreateUrlRequest(url, 'PUT')
    commentData = PrepareCommentData(commentTextForSend)

    try:
        urllib.request.urlopen(urlRequest, data=commentData)
    except urllib.error.URLError as ex:
        PrintErrorMsg(ui, ("<Hack&Plan incoming hook> [%s] " % __name__) + str(ex))
        return


def SendNewComment(inTaskId, inCommitMessages):
    url = 'https://api.hacknplan.com/v0/projects/{project}/workitems/{task}/comments/'.format(
        project=projectId, task=inTaskId,
    )
    commentTextForSend = commentHeader + ''.join(inCommitMessages)
    urlRequest = CreateUrlRequest(url, 'POST')
    commentData = PrepareCommentData(commentTextForSend)

    try:
        urllib.request.urlopen(urlRequest, data=commentData)
    except urllib.error.URLError as ex:
        PrintErrorMsg(ui, ("<Hack&Plan incoming hook> [%s] " % __name__) + str(ex))
        return


########################
#   Utility methods
########################

def CreateUrlRequest(url, inMethod):
    request = urllib.request.Request(url, method=inMethod)
    request.add_header('Authorization', 'ApiKey %s' % apiKey)
    request.add_header('Content-Type', 'application/json')
    request.add_header('User-Agent', 'Mercurial/5.8')
    return request


def PrepareCommentData(commentText):
    return ('"%s"' % commentText).encode("utf-8")


def GetHookUserName():
    username = None
    if os.path.exists(cacheFilePath):
        cachedData = json.load(open(cacheFilePath))
        if ('AccountUsername' in cachedData):
            username = cachedData['AccountUsername']
    if username is None:
        url = 'https://api.hacknplan.com/v0/users/me'
        urlRequest = CreateUrlRequest(url, 'GET')

        try:
            response = urllib.request.urlopen(urlRequest)
        except urllib.error.URLError as ex:
            PrintErrorMsg(ui, ("<Hack&Plan incoming hook> [%s] " % __name__) + str(ex))
            return

        receivedData = ResponseToJson(response)
        username = receivedData['username']
        with open(cacheFilePath, 'w') as outfile:
            json.dump({'AccountUsername': username}, outfile)
    return username


def ResponseToJson(response):
    return json.loads(response.read().decode(response.info().get_param('charset') or 'utf-8'))


def IsOldComment(inCommentItem, inUserName):
    return inCommentItem['user']['username'] == inUserName


def GetCommentsItemsForTask(inTaskId):
    url = 'https://api.hacknplan.com/v0/projects/{project}/workitems/{task}/comments'.format(
        project=projectId, task=inTaskId,
    )

    urlRequest = CreateUrlRequest(url, 'GET')

    try:
        response = urllib.request.urlopen(urlRequest)
    except urllib.error.URLError as ex:
        PrintErrorMsg(ui, ("<Hack&Plan incoming hook> [%s] " % __name__) + str(ex))
        return

    receivedData = ResponseToJson(response)
    return receivedData['items']


def FormatCommitMessage(inHash, inUser, inDescription):
    description = inDescription.strip()
    lineBreakCharIndex = description.find("\n")
    if lineBreakCharIndex >= 0:
        title = description[:lineBreakCharIndex].strip()
    else:
        title = description
    title = FixDescriptionForTableRow(title)
    return commitTableRowFormat.format(rev=inHash, user=inUser, title=title)


def ParseTaskIds(inText):
    return TASK_REGEX.findall(inText)


def FixDescriptionForTableRow(inText):
    inText = inText.replace('|', '&#124;')
    return inText.replace('\n', ' ')


def GetCommentItemForEdit(inCommentItems, inUserName):
    for inCommentItem in inCommentItems:
        if IsOldComment(inCommentItem, inUserName):
            return inCommentItem
    return None
