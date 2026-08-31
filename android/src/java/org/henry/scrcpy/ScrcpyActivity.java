package org.henry.scrcpy;

import android.content.Context;
import android.util.Log;
import org.kivy.android.PythonActivity;

public class ScrcpyActivity extends PythonActivity {
    private static final String TAG = "ScrcpyActivity";
    private static DummySensorManager mDummySensor = null;

    @Override
    public Object getSystemService(String name) {
        if (Context.SENSOR_SERVICE.equals(name)) {
            Log.w(TAG, "Providing safe DummySensorManager in ScrcpyActivity to prevent Samsung JNI abort and NPE");
            if (mDummySensor == null) {
                mDummySensor = new DummySensorManager();
            }
            return mDummySensor;
        }
        return super.getSystemService(name);
    }
}
