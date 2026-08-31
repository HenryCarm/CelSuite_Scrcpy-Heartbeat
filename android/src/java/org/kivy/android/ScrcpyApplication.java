package org.kivy.android;

import android.app.Application;
import android.content.Context;
import android.util.Log;
import org.henry.scrcpy.DummySensorManager;

public class ScrcpyApplication extends Application {
    private static final String TAG = "ScrcpyApplication";
    private static DummySensorManager mDummySensor = null;

    @Override
    public Object getSystemService(String name) {
        if (Context.SENSOR_SERVICE.equals(name)) {
            Log.w(TAG, "Providing safe DummySensorManager in ScrcpyApplication");
            if (mDummySensor == null) {
                mDummySensor = new DummySensorManager();
            }
            return mDummySensor;
        }
        return super.getSystemService(name);
    }
}