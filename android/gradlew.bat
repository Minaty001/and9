@echo off
setlocal enabledelayedexpansion

set "DIRNAME=%~dp0"
if "%DIRNAME%"=="" set "DIRNAME=."
set "APP_HOME=%DIRNAME%"
set "WRAPPER_JAR=%APP_HOME%gradle\wrapper\gradle-wrapper.jar"
set "SHARED_JAR=%APP_HOME%gradle\wrapper\gradle-wrapper-shared.jar"

if defined JAVA_HOME (
    set "JAVA_EXE=%JAVA_HOME%\bin\java.exe"
) else (
    set "JAVA_EXE=java"
)

if not exist "%WRAPPER_JAR%" goto missing
if not exist "%SHARED_JAR%" goto missing
goto run

:missing
echo [ERROR] Gradle wrapper JAR not found at %WRAPPER_JAR%
echo [ERROR] Gradle wrapper shared JAR not found at %SHARED_JAR%
exit /b 1

:run
"%JAVA_EXE%" -Xmx64m -Xms64m -classpath "%WRAPPER_JAR%;%SHARED_JAR%" org.gradle.wrapper.GradleWrapperMain %*
