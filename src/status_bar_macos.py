from status_bar_base import StatusBarBase, Status
import rumps
from rumps import MenuItem, Timer


class MacOSBar(StatusBarBase):
    
    def __init__(self, config, status_callback):
        super(MacOSBar, self).__init__(config, status_callback)
        self._create_mparts = {
                Status.idle         : self._create_idle_mpart,
                Status.uploading    : self._create_uploading_mpart,
                Status.paused       : self._create_paused_mpart,
                Status.auth_needed  : self._create_auth_mpart}
        self._icons = {
                Status.idle         : 'res/duck.jpg',
                Status.uploading    : 'res/up.jpg',
                Status.paused       : 'res/pause.jpg',
                Status.auth_needed  : 'res/pause.jpg'}
        self._item_progress = MenuItem('0% uploaded', callback=None)
        self._item_pause    = MenuItem('Pause upload', callback=self._pause_clicked)
        self._item_continue = MenuItem('Continue upload', callback=self._continue_clicked)
        self._item_auth     = MenuItem('Authentication in progress', callback=None)
        self._item_info     = MenuItem('Info', callback=self._info_clicked)
        self._item_settings = MenuItem('Settings', callback=self._settings_clicked)
        menu_list = self._create_menu()
        self._bar = rumps.App('GDriveDormouse',
                              icon=self._icons[self.status],
                              template=True,
                              menu=menu_list)
        self._timer = Timer(self.process_events, 1)
        self._last_status = self.status
                           
#   @overrides(StatusBarBase)
    def _update(self):
        if self.status == Status.uploading:
            percents = int(self.progress * 100)
            progress_str = '{}% uploaded'.format(percents)
            self._log.debug('updating progres to "%s"', progress_str)
            self._item_progress.title = progress_str
        if self._last_status == self.status:
            self._log.debug('New & Old status are the same, ignoring')
            return
        self._bar.menu.clear()
        self._bar.menu = self._create_menu() + [self._bar.quit_button]
        self._bar.icon = self._icons[self.status]
        self._last_status = self.status
        self._log.info('Updated status bar for status "%s"', str(self.status))
        
#   @overrides(StatusBarBase)
    def run(self):
        self._timer.start()
        self._bar.run()

    def _create_menu(self):
        top = self._create_mparts[self.status]()
        bottom = [self._item_info, self._item_settings]
        return top + bottom
        
    def _create_idle_mpart(self):
        return []
        
    def _create_uploading_mpart(self):
        return [self._item_progress, self._item_pause]
                
    def _create_paused_mpart(self):
        return [self._item_continue]

    def _create_auth_mpart(self):
        return [self._item_auth]

    def _pause_clicked(self):
        self._log.info('Pause clicked')
        self.status = Status.paused
    
    def _continue_clicked(self):
        self._log.info('Continue clicked')
        self.status = Status.uploading
    
    def _info_clicked(self):
        self._log.info('Info clicked')
        pass
    
    def _settings_clicked(self):
        self._log.info('Settings clicked')
        pass
