# ===

    def _start_supervisor(self):
        config = self._get_config()
        
        def create_gdrive():
            auth = self._authenticate(
                        GoogleAuth(settings_file=config['gauth_settings']))
            drive = GoogleDrive(auth)
            return drive
            
        def create_gdrive_sync():
            self._mutex.acquire()
            try:
                return create_gdrive()
            finally:
                self._mutex.release()
        
        self._uploads_supervisor = UploadsSupervisor(
                                        create_gdrive_sync(), 
                                        config['uploader_jobs_path'], 
                                        config['gdrive_dst_path'],
                                        config['ignore_file_names'])
                 
    def _authenticate(self, auth):
        if not auth.access_token_expired:
            return auth
        self._auth_needed = True
        self._update()
        try:
            auth.Refresh()
        except RefreshError as e:
            self._log.warn('GoogleAuth.Refresh() error %s', str(e))
            self._log.info('Will authenticate with local web server')
            auth.LocalWebserverAuth()
        self._auth_needed = False
        self._update()
        return auth
