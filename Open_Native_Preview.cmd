@echo off
setlocal
set "BLENDER=C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
if not "%~1"=="" set "BLENDER=%~1"
if not exist "%BLENDER%" (
  echo Pass the path to your Blender executable as the first argument.
  pause
  exit /b 1
)
start "Neural Finishing Preview" "%BLENDER%" "%~dp0demo\neural_finishing_demo.blend" --disable-autoexec --python "%~dp0tools\preview_in_blender.py"
exit /b 0
