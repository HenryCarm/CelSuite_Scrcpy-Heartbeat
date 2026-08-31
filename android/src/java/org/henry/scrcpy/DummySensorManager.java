package org.henry.scrcpy;

import android.hardware.Sensor;
import android.hardware.SensorAdditionalInfo;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.os.Handler;

import java.util.Collections;
import java.util.List;

public class DummySensorManager extends SensorManager {
    @Override
    public List<Sensor> getSensorList(int type) {
        return Collections.emptyList();
    }

    @Override
    public Sensor getDefaultSensor(int type) {
        return null;
    }

    @Override
    public Sensor getDefaultSensor(int type, boolean wakeUp) {
        return null;
    }

    @Override
    protected List<Sensor> getFullSensorList() {
        return Collections.emptyList();
    }

    @Override
    protected List<Sensor> getFullDynamicSensorList() {
        return Collections.emptyList();
    }

    @Override
    protected boolean registerListenerImpl(SensorEventListener listener, Sensor sensor, int delayUs, Handler handler, int maxBatchReportLatencyUs, int reservedFlags) {
        return false;
    }

    @Override
    protected void unregisterListenerImpl(SensorEventListener listener, Sensor sensor) {
    }

    @Override
    protected boolean flushImpl(SensorEventListener listener) {
        return false;
    }

    @Override
    protected boolean initDataInjectionImpl(boolean enable, int reserved) {
        return false;
    }

    @Override
    protected boolean injectSensorDataImpl(Sensor sensor, float[] values, int accuracy, long timestamp) {
        return false;
    }

    @Override
    protected boolean setOperationParameterImpl(SensorAdditionalInfo parameter) {
        return false;
    }
}
