package org.kivy.android;

import android.app.Application;
import android.content.Context;
import android.util.Log;

public class ScrcpyApplication extends Application {
    private static final String TAG = "ScrcpyApplication";

    @Override
    public Object getSystemService(String name) {
        if (Context.SENSOR_SERVICE.equals(name)) {
            Log.w(TAG, "Blocked SENSOR_SERVICE in Application context");
            return null;
        }
        return super.getSystemService(name);
    }
}