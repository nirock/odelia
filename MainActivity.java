package org.omer.odelia.odelia;

import android.media.AudioManager;
import android.media.ToneGenerator;
import android.net.Uri;
import android.os.PowerManager;
import android.support.v7.app.AppCompatActivity;
import android.os.Bundle;

import com.google.android.gms.appindexing.Action;
import com.google.android.gms.appindexing.AppIndex;
import com.google.android.gms.appindexing.Thing;
import com.google.android.gms.common.api.GoogleApiClient;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.Socket;
import java.net.UnknownHostException;
import java.nio.ByteBuffer;
import java.util.Arrays;

public class MainActivity extends AppCompatActivity {
    void play_tone(ToneGenerator tone_generator, int tone) {
        tone_generator.startTone(tone);
        try {
            Thread.sleep(100);
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
        tone_generator.stopTone();
    }

    /**
     * ATTENTION: This was auto-generated to implement the App Indexing API.
     * See https://g.co/AppIndexing/AndroidStudio for more information.
     */
    private GoogleApiClient client;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        new Thread() {
            @Override
            public void run() {
                // Make the device CPU always wake
                PowerManager powerManager = (PowerManager) getSystemService(POWER_SERVICE);
                PowerManager.WakeLock wakeLock = powerManager.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK,
                        "MyWakelockTag");
                wakeLock.acquire();

                ToneGenerator tone_generator = new ToneGenerator(AudioManager.STREAM_MUSIC, 100);
                Socket socket = null;

                while (true) {
                    try {
                        socket = new Socket("odelia.zapto.org", 1221);

                        byte[] buffer = new byte[1024];
                        ByteBuffer wrapped = null;

                        InputStream inputStream = socket.getInputStream();
                        OutputStream outputStream = socket.getOutputStream();

                        while (true) {
                            if (-1 == inputStream.read(buffer, 0, 4)) {
                                break;
                            }
                            int size = wrapped.wrap(buffer).getInt();
                            if (-1 == inputStream.read(buffer, 0, size)) {
                                break;
                            }
                            int command = wrapped.wrap(buffer).get();
                            switch (command) {
                                case 0:
                                    play_tone(tone_generator, ToneGenerator.TONE_DTMF_8);
                                    break;
                                case 1:
                                    play_tone(tone_generator, ToneGenerator.TONE_DTMF_2);
                                    break;
                                case 2:
                                    play_tone(tone_generator, ToneGenerator.TONE_DTMF_6);
                                    break;
                                case 3:
                                    play_tone(tone_generator, ToneGenerator.TONE_DTMF_4);
                                    break;
                                case 4:
                                    play_tone(tone_generator, ToneGenerator.TONE_DTMF_5);
                                    break;
                            }
                        }

                    } catch (UnknownHostException e) {
                        e.printStackTrace();
                        // response = "UnknownHostException: " + e.toString();
                    } catch (IOException e) {
                        e.printStackTrace();
                        // response = "IOException: " + e.toString();
                    } catch (Exception e) {
                        e.printStackTrace();
                    } finally {
                        if (socket != null) {
                            try {
                                socket.close();
                                socket = null;
                            } catch (IOException e) {
                                // TODO Auto-generated catch block
                                e.printStackTrace();
                            }
                        }
                    }
                }
            }
        }.start();

        new Thread() {
            @Override
            public void run() {
                Socket socket = null;
                DatagramSocket socket2 = null;
                int bytes_read = -1;
                while (true) {
                    try {
                        socket = new Socket("127.0.0.1", 8080);
                        socket2 = new DatagramSocket();
                        InetAddress IPAddress =  InetAddress.getByName("odelia.zapto.org");

                        InputStream inputStream = socket.getInputStream();
                        OutputStream outputStream = socket.getOutputStream();
                        byte[] buffer = new byte[65536];
                        String get_image = "GET /video HTTP/1.1\r\n\r\n";
                        byte[] get_image_byte_array = get_image.getBytes();
                        outputStream.write(get_image_byte_array, 0, get_image_byte_array.length);
                        while (true) {
                            bytes_read = inputStream.read(buffer, 0, 65536);
                            if (-1 == bytes_read) {
                                break;
                            };
                            DatagramPacket send_packet = new DatagramPacket(buffer, bytes_read, IPAddress, 1222);
                            socket2.send(send_packet);
                        }
                    } catch (UnknownHostException e) {
                        e.printStackTrace();
                        // response = "UnknownHostException: " + e.toString();
                    } catch (IOException e) {
                        e.printStackTrace();
                        // response = "IOException: " + e.toString();
                    } catch (Exception e) {
                        e.printStackTrace();
                    } finally {
                        if (socket != null) {
                            try {
                                socket.close();
                                socket = null;
                                socket2.close();
                                socket2 = null;
                            } catch (IOException e) {
                                // TODO Auto-generated catch block
                                e.printStackTrace();
                            }
                        }
                    }
                }
            }
        }.start();

        // ATTENTION: This was auto-generated to implement the App Indexing API.
        // See https://g.co/AppIndexing/AndroidStudio for more information.
        client = new GoogleApiClient.Builder(this).addApi(AppIndex.API).build();
    }

    /**
     * ATTENTION: This was auto-generated to implement the App Indexing API.
     * See https://g.co/AppIndexing/AndroidStudio for more information.
     */
    public Action getIndexApiAction() {
        Thing object = new Thing.Builder()
                .setName("Main Page") // TODO: Define a title for the content shown.
                // TODO: Make sure this auto-generated URL is correct.
                .setUrl(Uri.parse("http://[ENTER-YOUR-URL-HERE]"))
                .build();
        return new Action.Builder(Action.TYPE_VIEW)
                .setObject(object)
                .setActionStatus(Action.STATUS_TYPE_COMPLETED)
                .build();
    }

    @Override
    public void onStart() {
        super.onStart();

        // ATTENTION: This was auto-generated to implement the App Indexing API.
        // See https://g.co/AppIndexing/AndroidStudio for more information.
        client.connect();
        AppIndex.AppIndexApi.start(client, getIndexApiAction());
    }

    @Override
    public void onStop() {
        super.onStop();

        // ATTENTION: This was auto-generated to implement the App Indexing API.
        // See https://g.co/AppIndexing/AndroidStudio for more information.
        AppIndex.AppIndexApi.end(client, getIndexApiAction());
        client.disconnect();
    }
}

