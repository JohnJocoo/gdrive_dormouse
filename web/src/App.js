import React from "react";
import {SettingsPane, SettingsPage, SettingsContent, SettingsMenu} from 'react-settings-pane';
import axios from "axios";
import Notifications, {notify} from 'react-notify-toast';

class App extends React.Component {
  constructor(props) {
    super(props);

    // You will maybe receive your settings from this.props or do a fetch request in your componentWillMount
    // but here is an example of how it should look like:
    this.state = {
      "settings.monitoring.path": "~/Pictures",
      "settings.monitoring.wait_time": 5,
      "settings.gdrive.path": "/GDriveDormouse",
      
      "settings.file_handler.ignore_names": "",
      "settings.file_handler.dirs_as_jobs": true,
      "settings.file_handler.add_time_job_name": true,
      "settings.file_handler.job_name_template": "%Y-%m-%d-%{name}",
      "settings.file_handler.partition": "general_type"
    };

    // Save settings after close
    this._leavePaneHandler = (wasSaved, newSettings, oldSettings) => {
      // "wasSaved" indicates wheather the pane was just closed or the save button was clicked.

      if (wasSaved && newSettings !== oldSettings) {
        // do something with the settings, e.g. save via ajax.
        axios.post("/api/v1.0/set-settings", newSettings)
            .then(function (response) {
                notify.show("Settings saved");
            })
            .catch(function (error) {
                notify.show("Failed to save settings: " + error.message, "error");
            });
      }
    };

    // React if a single setting changed
    this._settingsChanged = ev => {
        let getValue = ev => {
            if (el.type.toLowerCase() == "checkbox") {
                return el.checked;    
            } 
            return el.value;
        };
        
        let el = ev.target;
        if (el.tagName.toUpperCase() == "INPUT") {
            this.state[el.name] = getValue(el);
        }
    };
    
    this._clearGDriveCreds = ev => {};
    
    this._loginToGDrive = ev => {};

    // Define your menu
    this._menu = [
      {
        title: "General", // Title that is displayed as text in the menu
        url: "/settings/general" // Identifier (url-slug)
      },
      {
        title: "Files handling",
        url: "/settings/files_handling"
      },
      {
        title: "About",
        url: "/settings/about"
      }
    ];
  }

  render() {
    // Get settings
    let settings = this.state;

    // Define one of your Settings pages
    /*
     const dynamicOptionsForGeneralPage = [
       {
         key: null
         label: 'Account',
         type: 'headline',
       },
       {
         key: 'mysettings.general.email',
         label: 'E-Mail address',
         type: 'text',
       },
       {
         key: 'mysettings.general.password',
         label: 'Password',
         type: 'password',
       },
       {
         key: 'mysettings.general.password-repeat',
         label: 'Password repeat',
         type: 'password',
       },
       {
         key: null,
         label: 'Appearance',
         type: 'headline',
       },
       {
         key: 'mysettings.general.color-theme',
         label: 'Color Theme',
         type: 'custom',
         component: <select><option value="blue">Blue</option><option value="red">Red</option></select>,
       }
     ];
     // Then use with:
     // <SettingsPage handler="/settings/general" options={dynamicOptionsForGeneralPage} />
     */

    // Return your Settings Pane
    return (
      <div className="md-root">
        <Notifications />
        <div ref={ref => (this.prefs = ref)} className="md-modal show">
          <SettingsPane
            items={this._menu}
            index="/settings/general"
            settings={settings}
            onChange={this._settingsChanged}
            onPaneLeave={this._leavePaneHandler}
          >
            <SettingsMenu headline="GDrive Dormouse Settings" />
            <SettingsContent header>
              <SettingsPage handler="/settings/general">
                <fieldset className="form-group">
                  <label htmlFor="monitoring.path">Local monitoring path: </label>
                  <input
                    type="text"
                    className="form-control"
                    name="settings.monitoring.path"
                    placeholder="Directory path"
                    id="monitoring.path"
                    onChange={this._settingsChanged}
                    defaultValue={settings["settings.monitoring.path"]}
                  />
                </fieldset>
                <fieldset className="form-group">
                  <label htmlFor="monitoring.wait_time">Waiting period in minutes until start job: </label>
                  <br/>
                  <label className="label-note">GDrive Dormouse will wait for this amount of minutes for no file changes before starting upload </label>
                  <input
                    type="number"
                    className="form-control"
                    name="settings.monitoring.wait_time"
                    placeholder="Minutes"
                    id="monitoring.wait_time"
                    min="1" 
                    max="60"
                    onChange={this._settingsChanged}
                    defaultValue={settings["settings.monitoring.wait_time"]}
                  />
                </fieldset>
                <fieldset className="form-group">
                  <label htmlFor="gdrive.path">Google Drive path to upload files: </label>
                  <input
                    type="text"
                    className="form-control"
                    name="settings.gdrive.path"
                    placeholder="Google Drive directory path"
                    id="gdrive.path"
                    onChange={this._settingsChanged}
                    defaultValue={settings["settings.gdrive.path"]}
                  />
                </fieldset>
                <fieldset className="form-group">
                  <label>Google Drive authentication: </label>
                  <div className="input-group">
                    <input
                      type="button"
                      className="btn btn-warning"
                      onClick={this._clearGDriveCreds}
                      value="Clear credentials"
                    />
                    <input
                      type="button"
                      className="btn btn-default input-group-button"
                      onClick={this._loginToGDrive}
                      value="Sign into Google Drive"
                    />
                  </div>
                </fieldset>
              </SettingsPage>
              
              <SettingsPage handler="/settings/files_handling">
                <fieldset className="form-group">
                  <div className="input-group2">
                    <input
                      type="checkbox"
                      className="form-check-input"
                      name="settings.file_handler.dirs_as_jobs"
                      id="file_handler.dirs_as_jobs"
                      onChange={this._settingsChanged}
                      defaultChecked={settings["settings.file_handler.dirs_as_jobs"]}
                    />
                    <label 
                      className="form-check-label" 
                      htmlFor="file_handler.dirs_as_jobs"
                    >Treat top-level directories as separate jobs </label>
                  </div>
                </fieldset>
                <fieldset className="form-group">
                  <div className="input-group2">
                    <input
                      type="checkbox"
                      className="form-check-input"
                      name="settings.file_handler.add_time_job_name"
                      id="file_handler.add_time_job_name"
                      onChange={this._settingsChanged}
                      defaultChecked={settings["settings.file_handler.add_time_job_name"]}
                    />
                    <label 
                      className="form-check-label" 
                      htmlFor="file_handler.add_time_job_name"
                    >Add date and time to a job name </label>
                  </div>
                </fieldset>
                <fieldset className="form-group">
                  <label htmlFor="file_handler.job_name_template">Job name template: </label>
                  <br/>
                  <label className="label-note">See datetime.strftime() for available format codes, plus {"%{name}"} stands for original job (directory) name</label>
                  <input
                    type="text"
                    className="form-control"
                    name="settings.file_handler.job_name_template"
                    placeholder="%Y-%m-%d-%H:%M:%S-%{name}"
                    id="file_handler.job_name_template"
                    onChange={this._settingsChanged}
                    defaultValue={settings["settings.file_handler.job_name_template"]}
                  />
                </fieldset>
                <fieldset className="form-group">
                  <label htmlFor="file_handler.ignore_names">Ignore file names: </label>
                  <input
                    type="text"
                    className="form-control"
                    name="settings.file_handler.ignore_names"
                    placeholder="Coma-separated list of file names"
                    id="file_handler.ignore_names"
                    onChange={this._settingsChanged}
                    defaultValue={settings["settings.file_handler.ignore_names"]}
                  />
                </fieldset>
                <fieldset className="form-group">
                  <label htmlFor="file_handler.partition">Files partition: </label>
                  <select
                    name="settings.file_handler.partition"
                    id="file_handler.partition"
                    className="form-control"
                    onChange={this._settingsChanged}
                    defaultValue={settings["settings.file_handler.partition"]}
                  >
                    <option value="none">None (leave folder structure untouched)</option>
                    <option value="extention">By file extention (use extention as directory name)</option>
                    <option value="general_type">By generic type (jpeg, raw, video, other)</option>
                  </select>
                </fieldset>
              </SettingsPage>
              
              <SettingsPage handler="/settings/about">
              <div className="page-about">
              <br/>
              &nbsp;&nbsp;Google Drive Dormouse as background upload daemon to upload your files
              (ex. images, videos, other files) to your Google Drive. It is designed to be 
              reliable uploader for large amount of files and unreliable network connection. 
              <br/>
              &nbsp;&nbsp;GDrive Dormouse will always retry upload or schedule retry for later.
              It will wait for time defined in settings until no new files in monitoring 
              folder added or existed modified. Then upload job will be created.
              <br/>
              <br/>
              <a href="https://github.com/JohnJocoo/gdrive_dormouse">GitHub page</a>
              <br/>
              <br/>
              Version {document.getElementById("_context_version").textContent}
              </div>
              </SettingsPage>
            </SettingsContent>
          </SettingsPane>
        </div>
      </div>
    );
  }
}

export default App;
