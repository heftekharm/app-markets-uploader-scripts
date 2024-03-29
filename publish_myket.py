
import hashlib
import requests
import os
import base64
import sys
import io

sys.stdout=io.TextIOWrapper(sys.stdout.detach(),encoding='utf-8')
sys.stderr=io.TextIOWrapper(sys.stderr.detach(),encoding='utf-8')

class MyketClient:
    def __init__(self, package_name, username, password):
        self.url = 'https://developer.myket.ir/api'
        self.resource_url = 'https://resource.myket.ir'
        self.raven_url = 'https://raven.myket.ir'
        self.package_name = package_name
        self.username = username
        self.password = password
        self._session_payload = dict()
        self._static_parameters = {'lang': 'fa'}

    @property
    def _token(self):
        return self._session_payload.get('token')

    @property
    def _account_id(self):
        return self._session_payload.get('accountId')

    @property
    def _secure_id(self):
        return self._session_payload.get('secureId')


    @property
    def _authentication_headers(self):
        self._ensure_authentication()
        # TODO: Check expiration
        return {'authorization': self._token }

    @property
    def _authentication_cookies(self):
        self._ensure_authentication()
        return {
            'myketAccessToken': self._token,
            'accountId': self._account_id,
            'secureId': self._secure_id,
        }

    def _ensure_authentication(self):
        """
        {
            'token': 'xxx',
            'accountId': 'xxx',
            'accountKey': 'xxx',
            'role': 'Developer',
            'is2Step': False,
            'result': 'Successful',
            'secureId': 'xxx'
         }
        :return:
        """
        if self._session_payload.get('token') is None:
            response = requests.post(
                f'{self.url}/dev-auth/signin/',
                params=self._static_parameters,
                data={
                    'identifier': self.username,
                    'retry': False,  # TODO:
                    'secret': hashlib.sha1(self.password.encode()).hexdigest(),
                    'verificationCode': '',  # TODO:
                }
            )
            result = response.json()
            #print(result)
            if not 200 <= response.status_code < 300:
                raise Exception(f'Login error: {result}')
            self._session_payload = result
            return result

    def get_new_version_constraints(self): 
        """
        :return: {'allowedAddRelease': True, 'allowedAddStagedRollout': True, 'isRollbackAllowed': True}
        """
        self._ensure_authentication()
        response = requests.get(
            f'{self.url}/developers/{self._account_id}/applications/{self.package_name}/new-release-constraints',
            params=self._static_parameters,
            headers=self._authentication_headers,
            cookies=self._authentication_cookies,
        )
        result = response.json()
        if not 200 <= response.status_code < 300:
            raise Exception(f'Get new version constraint error: {result}')
        return result

    def upload_apk(self, apk_path):
        """
        :param apk_path: Apk file path
        :return: Link of the apk
        """
        self._ensure_authentication()
        initial_headers=self._authentication_headers.copy()
        initial_headers["Tus-Resumable"]="1.0.0"
        session = requests.Session()
        file_size = os.path.getsize(apk_path)
        file_name = apk_path.split('/')[-1]    
        session.headers.update(initial_headers)
        initial_response=session.post(self.raven_url + "/developers/apk/" , headers={
            "Upload-Length":str(file_size),
            "Upload-Metadata":f'filename {base64.b64encode(file_name.encode("ascii")).decode("ascii")},filetype YXBwbGljYXRpb24vdm5kLmFuZHJvaWQucGFja2FnZS1hcmNoaXZl'
            })
        if initial_response.status_code == 201 :
            upload_path = initial_response.headers["Location"]
            upload_url=self.raven_url + upload_path
            upload_offset = 0
            print("upload url is " + upload_url)
            with open(apk_path,'rb') as file:
                while(upload_offset < file_size):
                    end_offset = min(upload_offset + 1024000, file_size)
                    chunk = file.read(end_offset - upload_offset)
                    print("chunk size is " + str(len(chunk)))
                    patch_response = session.patch(upload_url,
                        headers={
                            "Upload-Offset": str(upload_offset),
                            "Content-Type": "application/offset+octet-stream"
                        },
                        data=chunk,
                    )
                    if patch_response.status_code == 204:
                        upload_offset = end_offset
                    else:
                        print("PATCH request failed with status code:", patch_response.status_code)
                        raise "upload failed"
            uuid=upload_url.split('/')[-1]
            apk_link=self.resource_url+"/Uploads/"+uuid+"/"+uuid+".apk"
            return apk_link            
        raise "upload failed"

    def validate(self, apk_link , version_code , min_sdk):
        self._ensure_authentication()
        response = requests.post(
            f'{self.url}/developers/{self._account_id}/applications/{self.package_name}/versions',
            params=self._static_parameters,
            headers=self._authentication_headers,
            cookies=self._authentication_cookies,
            json={
                'ApkLink': apk_link,
            }
        )
        result = response.json()
        if not 200 <= response.status_code < 300:
            raise Exception(f'Release commit error: {result}')        
        response = requests.post(
            f'{self.url}/developers/{self._account_id}/applications/{self.package_name}/validate',
            params=self._static_parameters,
            headers=self._authentication_headers,
            cookies=self._authentication_cookies,
            json={
                'versions': [{
                    "versionCode":version_code,"sdk":min_sdk
                }]
            }
        )
        return result

    def draft(self,apk_link,version_name,changelist_fa="",changelist_en="",rollout_percent=10):
        self._ensure_authentication()
        response = requests.post(
            f'{self.url}/developers/{self._account_id}/applications/{self.package_name}/releases',
            params=self._static_parameters,
            headers=self._authentication_headers,
            cookies=self._authentication_cookies,
            json={
                "title":version_name,
                'stagedRolloutPercent': rollout_percent,
                'translationInfos': [
                    {'description': '<p>'+changelist_fa+'</p>', 'language': 'Fa'},
                    {'description': '<p>'+changelist_en+'</p>', 'language': 'En'},
                ],
                'versions':[
                    {
                        "apkLink":apk_link,
                        "case":0
                    }
                ]

            }
        )
        result = response.json()
        if not 200 <= response.status_code < 300:
            raise Exception(f'Release publish error: {result}')
        print("drafted")
        return result


if __name__ == '__main__':
    username = "your developer account username on Myket"
    password = "your developer account password on Myket"
    package_name = "PACKAGE_NAME"
    apk_path = "APK_PATH"
    version_code = "VERSION_CODE"
    version_name = "VERSION_NAME"
    min_sdk = "MIN_SDK"
    changelist_fa_path = "./CHANGELIST_FA.txt"
    changelist_en_path = "./CHANGELIST_EN.txt"        


    print("package name is " + package_name)
    print("apk path is " + apk_path)
    print("version code is " + version_code)
    print("version name is " + version_name)
    print("minimum sdk is " + min_sdk)
    print("Farsi Changelist file is " + changelist_fa_path)
    print("English Changelist file is " + changelist_en_path)

    client = MyketClient(package_name, username, password)

    print(f'\nGetting new version constraints...')
    constraints = client.get_new_version_constraints()
    print(f'Done getting new version constraints: {constraints}')
    
    print(f'\nUploading a new release...')
    apk_link = client.upload_apk(apk_path)
    print(f'\nUploaded... at ' + apk_link )
    
    rollout_response = client.validate(
        apk_link,
        version_code,
        min_sdk
    )

    print(f'\nApk Link Validated ')
    changelist_fa_content = open(changelist_fa_path , "r", encoding = "utf8").read()
    changelist_en_content = open(changelist_en_path , "r", encoding = "utf8").read()
    publish_response = client.draft(apk_link,version_name,changelist_fa_content,changelist_en_content)
    print(f'The release is drafted successfully')
    print(f'Go to Myket and publish it')
