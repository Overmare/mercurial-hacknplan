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


def reportToHacknPlan(ui, repo, node, **kwargs):
    global apiKey
    global projectId
    global commentHeader
    global commitTableRowFormat
    global mercurialUI

    try:
        secrets = json.load(open(secretsFilePath))
    except (IOError, ValueError) as ex:
        printErrorMsg(
            "Hack-n-Plan incoming hook could not load secrets because %s \nand.. stopped execution ¯\_(ツ)_/¯" % str(ex))

    apiKey = secrets['apiKey']
    projectId = secrets['projectId']
    commentHeader = secrets['commentHeader']
    commitTableRowFormat = secrets['commitTableRowFormat']

    mercurialUI = ui
    hookUserName = getHookUserName()
    commitInfo = repo[node]

    rawCommitDescription = commitInfo.description().decode("utf-8")
    taskIds = parseTaskIds(rawCommitDescription)

    if len(taskIds) == 0:
        return

    commitUser = commitInfo.user().decode("utf-8")
    commitHash = commitInfo.hex()[:12].decode("utf-8")
    commitDescription = formatCommitMessage(commitHash, commitUser, rawCommitDescription)

    for taskId in taskIds:
        comments = getCommentsItemsForTask(taskId)
        existingComment = getCommentItemForEdit(comments, hookUserName)
        if existingComment != None:
            editOldComment(existingComment, commitDescription)
        else:
            sendNewComment(taskId, commitDescription)


########################
#   Main Actions
########################

def editOldComment(inCommentItem, inCommitMessages):
    taskId = inCommentItem['workItemId']
    commentId = inCommentItem['commentId']
    commentTextForSend = inCommentItem['text'] + ''.join(inCommitMessages)
    url = 'https://api.hacknplan.com/v0/projects/%s/workitems/%s/comments/%s' % (projectId, taskId, commentId)
    urlRequest = createUrlRequest(url, 'PUT')
    commentData = prepareCommentData(commentTextForSend)

    try:
        urllib.request.urlopen(urlRequest, data=commentData)
    except urllib.error.URLError as ex:
        printErrorMsg(("<Hack&Plan incoming hook> [%s] " % __name__) + str(ex))


def sendNewComment(inTaskId, inCommitMessages):
    url = 'https://api.hacknplan.com/v0/projects/%s/workitems/%s/comments/' % (projectId, inTaskId)
    commentTextForSend = commentHeader + ''.join(inCommitMessages)
    urlRequest = createUrlRequest(url, 'POST');
    commentData = prepareCommentData(commentTextForSend)

    try:
        urllib.request.urlopen(urlRequest, data=commentData)
    except urllib.error.URLError as ex:
        printErrorMsg(("<Hack&Plan incoming hook> [%s] " % __name__) + str(ex))


########################
#   Utility methods
########################

def createUrlRequest(url, inMethod):
    request = urllib.request.Request(url, method=inMethod)
    request.add_header('Authorization', 'ApiKey %s' % apiKey)
    request.add_header('Content-Type', 'application/json')
    request.add_header('User-Agent', 'Mercurial/5.8')
    return request


def prepareCommentData(commentText):
    return ('"%s"' % commentText).encode("utf-8")


def printErrorMsg(msg):
    mercurialUI.write((msg + "\n").encode("utf-8"))


def getHookUserName():
    username = None
    if os.path.exists(cacheFilePath):
        cachedData = json.load(open(cacheFilePath))
        if ('AccountUsername' in cachedData):
            username = cachedData['AccountUsername']
    if username is None:
        url = 'https://api.hacknplan.com/v0/users/me'
        urlRequest = createUrlRequest(url, 'GET')

        try:
            response = urllib.request.urlopen(urlRequest)
        except urllib.error.URLError as ex:
            printErrorMsg(("<Hack&Plan incoming hook> [%s] " % __name__) + str(ex))

        receivedData = responseToJson(response)
        username = receivedData['username']
        with open(cacheFilePath, 'w') as outfile:
            json.dump({'AccountUsername': username}, outfile)
    return username


def responseToJson(response):
    return json.loads(response.read().decode(response.info().get_param('charset') or 'utf-8'))


def isOldComment(inCommentItem, inUserName):
    return inCommentItem['user']['username'] == inUserName


def getCommentsItemsForTask(inTaskId):
    url = 'https://api.hacknplan.com/v0/projects/%s/workitems/%s/comments' % (projectId, inTaskId)
    urlRequest = createUrlRequest(url, 'GET')

    try:
        response = urllib.request.urlopen(urlRequest)
    except urllib.error.URLError as ex:
        printErrorMsg(("<Hack&Plan incoming hook> [%s] " % __name__) + str(ex))

    receivedData = responseToJson(response)
    return receivedData['items']


def formatCommitMessage(inHash, inUser, inDescription):
    description = inDescription.strip()
    lineBreakCharIndex = description.find("\n")
    if lineBreakCharIndex >= 0:
        title = description[:lineBreakCharIndex].strip()
    else:
        title = description
    title = fixDescriptionForTableRow(title)
    return commitTableRowFormat % (inHash, inHash, inUser, title)


def parseTaskIds(inText):
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


def fixDescriptionForTableRow(inText):
    inText = inText.replace('|', '&#124;')
    return inText.replace('\n', ' ')


def getCommentItemForEdit(inCommentItems, inUserName):
    for inCommentItem in inCommentItems:
        if isOldComment(inCommentItem, inUserName):
            return inCommentItem
    return None
