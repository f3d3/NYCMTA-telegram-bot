import os
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive


async def google_drive_backup(*args):

    context = args[0]
    folderName = context.job.data

    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()
    # gauth.CommandLineAuth()
    drive = GoogleDrive(gauth)

    # List folders
    folders = drive.ListFile(
        {'q': "title='" + folderName + "' and mimeType='application/vnd.google-apps.folder' and trashed=false"}).GetList()

    # Create new folder if it doesn't exist
    if len(folders)==0:
        folder = drive.CreateFile({'title' : folderName, 'mimeType' : 'application/vnd.google-apps.folder'})
        folder.Upload()
        folders = drive.ListFile(
        {'q': "title='" + folderName + "' and mimeType='application/vnd.google-apps.folder' and trashed=false"}).GetList()

    # Upload files to the specific folder after getting the folder id
    for folder in folders:
        if folder['title'] == folderName:
            file_list = drive.ListFile({'q': "'"+folder['id']+"'" + " in parents and trashed=false"}).GetList()

            if len(file_list)==0: # folder is empty and files do not already exist
                file1 = drive.CreateFile({'title': 'my_persistence', 'parents': [{'id': folder['id']}]})
                file1.SetContentFile(os.getcwd()+'/my_persistence')
                file1.Upload()
                file2 = drive.CreateFile({'title': 'PicklePersistence', 'parents': [{'id': folder['id']}]})
                file2.SetContentFile(os.getcwd()+'/PicklePersistence')
                file2.Upload()
            else: # folder is not empty, check existing files and, if existent, replace them by specifyng the file id
                for x in range(len(file_list)): # files 
                    if file_list[x]['title'] == 'my_persistence':
                        file_id_1 = file_list[x]['id']
                        file1 = drive.CreateFile({'id':file_id_1, 'title': 'my_persistence', 'parents': [{'id': folder['id']}]})
                        file1.SetContentFile(os.getcwd()+'/my_persistence')
                        file1.Upload()
                    elif file_list[x]['title'] == 'PicklePersistence':
                        file_id_2 = file_list[x]['id']
                        file2 = drive.CreateFile({'id':file_id_2, 'title': 'PicklePersistence', 'parents': [{'id': folder['id']}]})
                        file2.SetContentFile(os.getcwd()+'/PicklePersistence')
                        file2.Upload()

