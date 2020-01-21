import React from "react";
import {SettingsPane, SettingsPage, SettingsContent, SettingsMenu} from 'react-settings-pane';

class App extends React.Component {
  constructor(props) {
    super(props);

    // You will maybe receive your settings from this.props or do a fetch request in your componentWillMount
    // but here is an example of how it should look like:
    this.state = {
      "settings.monitoring.path": "~/Pictures",
      "settings.monitoring.wait_time": 5,
      "settings.gdrive.path": "/GDriveDormouse",
      "mysettings.general.email": "dstuecken@react-settings-pane.com",
      "mysettings.general.picture": "earth",
      "mysettings.profile.firstname": "Dennis",
      "mysettings.profile.lastname": "Stücken"
    };

    // Save settings after close
    this._leavePaneHandler = (wasSaved, newSettings, oldSettings) => {
      // "wasSaved" indicates wheather the pane was just closed or the save button was clicked.

      if (wasSaved && newSettings !== oldSettings) {
        // do something with the settings, e.g. save via ajax.
      }

      this.hidePrefs();
    };

    // React if a single setting changed
    this._settingsChanged = ev => {};
    
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

  hidePrefs() {
    this.prefs.className = "md-modal";
  }

  showPrefs() {
    this.prefs.className = "md-modal show";
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
        <div ref={ref => (this.prefs = ref)} className="md-modal show">
          <SettingsPane
            items={this._menu}
            index="/settings/general"
            settings={settings}
            onChange={this._settingsChanged}
            onPaneLeave={this._leavePaneHandler}
          >
            <SettingsMenu headline="General Settings" />
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
                  <label htmlFor="profileFirstname">Firstname: </label>
                  <input
                    type="text"
                    className="form-control"
                    name="mysettings.profile.firstname"
                    placeholder="Firstname"
                    id="profileFirstname"
                    onChange={this._settingsChanged}
                    defaultValue={settings["mysettings.profile.firstname"]}
                  />
                </fieldset>
                <fieldset className="form-group">
                  <label htmlFor="profileLastname">Lastname: </label>
                  <input
                    type="text"
                    className="form-control"
                    name="mysettings.profile.lastname"
                    placeholder="Lastname"
                    id="profileLastname"
                    onChange={this._settingsChanged}
                    defaultValue={settings["mysettings.profile.lastname"]}
                  />
                </fieldset>
                <fieldset className="form-group">
                  <label htmlFor="profileBiography">Biography: </label>
                  <textarea
                    className="form-control"
                    name="mysettings.profile.biography"
                    placeholder="Biography"
                    id="profileBiography"
                    onChange={this._settingsChanged}
                    defaultValue={settings["mysettings.profile.biography"]}
                  />
                </fieldset>
                <fieldset className="form-group">
                  <label htmlFor="profileColor">Color-Theme: </label>
                  <select
                    name="mysettings.general.color-theme"
                    id="profileColor"
                    className="form-control"
                    defaultValue={settings["mysettings.general.color-theme"]}
                  >
                    <option value="blue">Blue</option>
                    <option value="red">Red</option>
                    <option value="purple">Purple</option>
                    <option value="orange">Orange</option>
                  </select>
                </fieldset>
              </SettingsPage>
            </SettingsContent>
          </SettingsPane>
        </div>
      </div>
    );
  }
}

export default App;
