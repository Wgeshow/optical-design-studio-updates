# Optical Design Studio

Version 1.0.4 provides a portable Windows x64 ZIP and configurable saved-data
location. Extract the ZIP and launch Optical Design Studio.exe. Data defaults to
User Data beside the program; choose another folder in Settings and restart.

Download the tested [Windows x64 portable ZIP](https://github.com/Wgeshow/optical-design-studio-downloads/releases/tag/v1.0.4).
No installer or separate Python setup is needed. Keep the extracted folder together.
Existing 1.0.3 installations need this ZIP downloaded manually once; 1.0.4 supports
anonymous ZIP update checks and verified downloads through About.

This is the public source repository. `main` contains stable source; `test` remains
available for experimental work before review and promotion to `main`. Visibility
applies to the whole repository, including its branches and commit history.

The app's update feed remains at `Wgeshow/optical-design-studio-downloads` so existing
copies continue to find releases. Source and dependency license notices are included
in the portable package. Research runs and user-uploaded material libraries are not.

See [src/README.md](src/README.md) for application and source setup instructions,
[packaging/PORTABLE.md](packaging/PORTABLE.md) for data folders and portable updates,
and [packaging/BUILDING.md](packaging/BUILDING.md) for build instructions. Source
execution requires Python 3.12 and a compatible native S4 build. The ZIP is tested
on Windows x64; Linux must be built and validated separately.

Before updating a portable installation, preserve `User Data` and
`portable_settings.json`. Changing the data folder in Settings takes effect after
restart and does not move or delete existing data.
