package com.hbm.handler;

import com.hbm.main.NuclearTechMod;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.URI;
import java.net.URL;
import java.util.ArrayList;
import java.util.List;

public class HTTPHandler {

    public static List<String> capsule = new ArrayList<>();
    public static List<String> tipOfTheDay = new ArrayList<>();

    public static void loadStats() {

        Thread resourceLoader = new Thread("NTM-Online-Resources") {

            @Override
            public void run() {
                try {
                    loadSoyuz();
                    loadTips();
                } catch(IOException e) {
                    NuclearTechMod.LOGGER.warn("Online resource loading failed!");
                }
            }

        };

        resourceLoader.start();
    }

    private static void loadSoyuz() throws IOException {

        URL github = URI.create("https://gist.githubusercontent.com/HbmMods/a1cad71d00b6915945a43961d0037a43/raw/soyuz_holo").toURL();
        BufferedReader in = new BufferedReader(new InputStreamReader(github.openStream()));

        String line;
        while((line = in.readLine()) != null) capsule.add(line);
        in.close();
    }

    private static void loadTips() throws IOException {

        URL github = URI.create("https://gist.githubusercontent.com/HbmMods/a03c66ba160184e12f43de826b30c096/raw/tip_of_the_day").toURL();
        BufferedReader in = new BufferedReader(new InputStreamReader(github.openStream()));

        String line;
        while((line = in.readLine()) != null) tipOfTheDay.add(line);
        in.close();
    }
}
