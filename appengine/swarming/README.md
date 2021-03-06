# Swarming

An AppEngine service to do task scheduling on highly hetegeneous fleets at
medium (10000s) scale. It is focused to survive network with low reliability,
high latency while still having low bot maintenance, and no server maintenance
at all since it's running on AppEngine.

Swarming is purely a task scheduler service.

[Documentation](doc)


## Setting up

*   Visit http://console.cloud.google.com and create a project. Replace
    `<appid>` below with your project id.
*   Visit Google Cloud Console
    *   IAM & Admin
        *   Click `Add Member` and add someone else so you can safely be hit by a
            bus.
        *   Create a new "Oauth 2.0 Client Id" of type "web application".  Make sure
            `https://<appid>.appspot.com` is an authorized JavaScript origin
            and `https://<appid>.appspot.com/oauth2callback` is an authorized
            redirect URL.  Replace \<client_id\> below with the created client id.
    *   Pub/Sub, click `Enable API`.
*   Upload the code with: `./tools/gae upl -x -A <appid>`
*   Visit https://\<appid\>.appspot.com/auth/bootstrap and click `Proceed`.
*   If you plan to use a [config service](../config_service),
    *   Make sure it is setup already.
    *   Make sure you set [SettingsCfg.ui_client_id](https://github.com/luci/luci-py/blob/master/appengine/swarming/proto/config.proto#L37)
        to be \<client_id\>
    *   [Follow instruction
        here](../components/components/config/#linking-to-the-config-service).

*   If you are not using a config service, see [Configuring using FS mode](https://github.com/luci/luci-py/blob/master/appengine/components/components/config/README.md#fs-mode).
    You'll need to add an entry to settings.cfg like `ui_client_id: "<client_id>"`

*   If you plan to use an [auth_service](../auth_service),
    *   Make sure it is setup already.
    *   [Follow instructions
        here](../auth_service#linking-other-services-to-auth_service).

*   Visit "_https://\<appid\>.appspot.com/auth/groups_":
    *   Create [access groups](doc/Access-Groups.md) as relevant. Visit the
        "_IP Whitelists_" tab and add bot external IP addresses if needed.

*   Visit "_https://\<appid\>.appspot.com/auth/oauth_config_":
    *   Make sure \<client_id\> is in the "List of known OAuth client IDs".
        If you are using an config_service, you'll need to modify this via the
        oauth.cfg file, not via the web UI.

*   Configure [bot_config.py](swarming_bot/config/bot_config.py) and
    [bootstrap.py](swarming_bot/config/bootstrap.py) as desired. Both are
    optional.

*   If using [machine_provider](../machine_provider),
    *   Ensure the `mp` parameter is enabled in the swarming
        [config](https://github.com/luci/luci-py/blob/master/appengine/swarming/proto/config.proto).
    *   Create a machine\_type entry in [bots.cfg](./proto/bots.proto) for each desired pool of bots.
*   Visit "_https://\<appid\>.appspot.com_" and follow the instructions to start
    a bot.
*   Visit "_https://\<appid\>.appspot.com/restricted/bots_" to ensure the bot is
    alive.
*   Run one of the [examples in the client code](../../client/example).
*   Tweak settings:
    *   Visit Google Cloud Console
        *   App Engine, Memcache, click `Change`:
            *   Choose "_Dedicated_".
            *   Set the cache to Dedicated 1Gb.
        *   App Engine, Settings, click `Edit`:
            *   Set Google login Cookie expiration to: 2 weeks, click Save.


## Running locally

You can run a swarming+isolate local setup with:

    ./tools/start_servers.py

Then run a bot with:

    ./tools/start_bot.py http://localhost:9050
