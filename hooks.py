import json
import os
import urllib

hookDirectory = os.path.dirname(os.path.abspath(__file__))
cacheFilePath = hookDirectory + "/HacknPlan_HookCache.json"
secretsFilePath = hookDirectory + "/HacknPlan_Settings.json"

apiKey = None
projectId = None
commentHeader = None
commitTableRowFormat = None
mercurialUI = None


def ReportToHacknPlan(ui, repo, node, **kwargs):
    global apiKey
    global projectId
    global commentHeader
    global commitTableRowFormat
    global mercurialUI

    try:
        secrets = json.load(open(secretsFilePath))
    except (IOError, ValueError) as ex:
        PrintErrorMsg("Hack-n-Plan incoming hook could not load secrets because %s \nand.. stopped execution ¯\_(ツ)_/¯" % str(ex))

    apiKey = secrets['apiKey']
    projectId = secrets['projectId']
    commentHeader = secrets['commentHeader']
    commitTableRowFormat = secrets['commitTableRowFormat']

    mercurialUI = ui
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
    url = f'https://api.hacknplan.com/v0/projects/{projectId}/workitems/{taskId}/comments/{commentId}'.format(
        projectId=projectId, taskId=taskId, commentId=commentId
    )
    urlRequest = CreateUrlRequest(url, 'PUT')
    commentData = PrepareCommentData(commentTextForSend)

    try:
        urllib.request.urlopen(urlRequest, data=commentData)
    except urllib.error.URLError as ex:
        PrintErrorMsg(("<Hack&Plan incoming hook> [%s] " % __name__) + str(ex))


def SendNewComment(inTaskId, inCommitMessages):
    url = 'https://api.hacknplan.com/v0/projects/%s/workitems/%s/comments/' % (projectId, inTaskId)
    commentTextForSend = commentHeader + ''.join(inCommitMessages)
    urlRequest = CreateUrlRequest(url, 'POST');
    commentData = PrepareCommentData(commentTextForSend)

    try:
        urllib.request.urlopen(urlRequest, data=commentData)
    except urllib.error.URLError as ex:
        PrintErrorMsg(("<Hack&Plan incoming hook> [%s] " % __name__) + str(ex))


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


def PrintErrorMsg(msg):
    mercurialUI.write((msg + "\n").encode("utf-8"))


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
            PrintErrorMsg(("<Hack&Plan incoming hook> [%s] " % __name__) + str(ex))

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
    url = 'https://api.hacknplan.com/v0/projects/%s/workitems/%s/comments' % (projectId, inTaskId)
    urlRequest = CreateUrlRequest(url, 'GET')

    try:
        response = urllib.request.urlopen(urlRequest)
    except urllib.error.URLError as ex:
        PrintErrorMsg(("<Hack&Plan incoming hook> [%s] " % __name__) + str(ex))

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
    words = inText.split()
    taskIds = []
    for word in words:
        taskIdWordIndex = word.find('#')
        if taskIdWordIndex != -1:
            word = word.replace('#', '')
            taskId = int(word)
            if taskId not in taskIds:
                taskIds.append(taskId)
    return taskIds


def FixDescriptionForTableRow(inText):
    inText = inText.replace('|', '&#124;')
    return inText.replace('\n', ' ')


def GetCommentItemForEdit(inCommentItems, inUserName):
    for inCommentItem in inCommentItems:
        if IsOldComment(inCommentItem, inUserName):
            return inCommentItem
    return None
