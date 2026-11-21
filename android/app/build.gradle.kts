plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)
}

val archiveRoot = rootProject.projectDir.parentFile
val reviewAssetsDir = layout.buildDirectory.dir("generated/gsi-review-assets")
val reviewAsset = reviewAssetsDir.map { it.file("data/reviews.json") }
val nodeSyncScript = File(archiveRoot, "src/android-sync.mjs")

val syncAndroidArchive = tasks.register<Exec>("syncAndroidArchive") {
    val siteCatalog = File(archiveRoot, "site/data/catalog.json")
    onlyIf { siteCatalog.isFile && nodeSyncScript.isFile }
    workingDir(archiveRoot)
    commandLine("node", nodeSyncScript.absolutePath, "--sync-assets", "--root", archiveRoot.absolutePath)
}

val exportAndroidReviews = tasks.register<Exec>("exportAndroidReviews") {
    dependsOn(syncAndroidArchive)
    val catalog = file("src/main/assets/data/catalog.json")
    val entries = File(archiveRoot, "entries")
    onlyIf { catalog.isFile && nodeSyncScript.isFile }
    inputs.file(catalog)
    inputs.files(fileTree(entries) { include("*.md") })
    inputs.file(nodeSyncScript)
    outputs.file(reviewAsset)
    workingDir(archiveRoot)
    commandLine(
        "node", nodeSyncScript.absolutePath,
        "--export-reviews",
        "--catalog", catalog.absolutePath,
        "--entries", entries.absolutePath,
        "--output", reviewAsset.get().asFile.absolutePath
    )
}

android {
    namespace = "com.gsi"
    compileSdk {
        version = release(37)
    }

    defaultConfig {
        applicationId = "com.gsi"
        minSdk = 37
        targetSdk = 37
        versionCode = 2
        versionName = "2.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        release {
            optimization {
                enable = true
                packageScope = setOf("androidx.**", "kotlin.**", "kotlinx.**")
            }
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
    buildFeatures {
        compose = true
    }
    sourceSets.getByName("main").assets.srcDir(reviewAssetsDir.get().asFile)
}

tasks.named("preBuild") { dependsOn(exportAndroidReviews) }

dependencies {
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.compose.animation)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.compose.material.icons.extended)
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.media3.exoplayer)
    implementation(libs.androidx.glance.appwidget)
    implementation(libs.androidx.glance.material3)
    testImplementation(libs.junit)
    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(libs.androidx.compose.ui.test.junit4)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(libs.androidx.junit)
    debugImplementation(libs.androidx.compose.ui.test.manifest)
    debugImplementation(libs.androidx.compose.ui.tooling)
}
