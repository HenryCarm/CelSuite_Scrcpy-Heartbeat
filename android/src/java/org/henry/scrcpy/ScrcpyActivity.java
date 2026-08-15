package org.henry.scrcpy;

import android.content.Context;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.View;
import org.kivy.android.PythonActivity;

public class ScrcpyActivity extends PythonActivity {
    private static final String TAG = "ScrcpyActivity";
    private DummySensorManager mDummySensorManager;

    @Override
    public Object getSystemService(String name) {
        if (Context.SENSOR_SERVICE.equals(name)) {
            Log.w(TAG, "Providing DummySensorManager to prevent Samsung JNI Modified UTF-8 crash");
            if (mDummySensorManager == null) {
                mDummySensorManager = new DummySensorManager();
            }
            return mDummySensorManager;
        }
        return super.getSystemService(name);
    }

    public void dismissLoadingView() {
        runOnUiThread(new Runnable() {
            @Override
            public void run() {
                try {
                    if (mProgress != null) {
                        mProgress.setVisibility(View.GONE);
                        if (mLayout != null) {
                            mLayout.removeView(mProgress);
                        }
                    }
                } catch (Exception e) {
                    Log.w(TAG, "Error dismissing mProgress: " + e.getMessage());
                }
            }
        });
    }

    @Override
    public void finishLoad() {
        try {
            super.finishLoad();
        } catch (Exception e) {
            Log.w(TAG, "Caught exception in finishLoad: " + e.getMessage());
        }
        dismissLoadingView();
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        try {
            super.onWindowFocusChanged(hasFocus);
        } catch (Exception e) {
            Log.w(TAG, "Safely caught exception in onWindowFocusChanged: " + e.getMessage());
        }
        if (hasFocus) {
            dismissLoadingView();
        }
    }

    @Override
    protected void onResume() {
        try {
            super.onResume();
        } catch (Exception e) {
            Log.w(TAG, "Safely caught exception in onResume: " + e.getMessage());
        }
        dismissLoadingView();
    }

    @Override
    protected void onPause() {
        try {
            super.onPause();
        } catch (Exception e) {
            Log.w(TAG, "Safely caught exception in onPause: " + e.getMessage());
        }
    }

    @Override
    protected void onStop() {
        try {
            super.onStop();
        } catch (Exception e) {
            Log.w(TAG, "Safely caught exception in onStop: " + e.getMessage());
        }
    }

    @Override
    protected void onDestroy() {
        try {
            super.onDestroy();
        } catch (Exception e) {
            Log.w(TAG, "Safely caught exception in onDestroy: " + e.getMessage());
        }
    }
}
