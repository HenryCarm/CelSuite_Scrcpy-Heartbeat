package org.henry.scrcpy;

import android.content.Context;
import android.util.Log;
import org.kivy.android.PythonActivity;

public class ScrcpyActivity extends PythonActivity {
    private static final String TAG = "ScrcpyActivity";

    @Override
    public Object getSystemService(String name) {
        if (Context.SENSOR_SERVICE.equals(name)) {
            Log.w(TAG, "Blocked SENSOR_SERVICE on Samsung device to prevent JNI Modified UTF-8 crash");
            return null;
        }
        return super.getSystemService(name);
    }
}
