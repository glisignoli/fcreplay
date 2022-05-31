# Development notes
## Setup
Use pipenv:
```
pipenv install
pipenv install --dev
```

## Tests
### Unit Tests
Some unittest are available by running
```
pytest
```

# Loading sample data
Ok, it's more like 'live data'. But it's handy for testing.
```
gunzip < ./files/sample-data.sql.gz | docker-compose exec -T postgres psql -U fcreplay -d fcreplay
```

### Functional test
A functional test is avilalable by running:
```
pytest --runslow -s fcreplay/tests/test_functionality.py
```

This will test most if not all features 

This will test all docker containers, except:
 - youtube/archive.org uploads
 - fcreplay-cli

## Database
The database is defined in `models.py`. Tested on postgresql
Interacting with the database should be done through the database class.
```python
from fcreplaydatabase import Database
db = Database()
```

## Running site locally:
Run with:
```
./dev_site.sh
```

Run with './dev_site.sh --debug' to enable debugpy debugging for vscode

## Processing order:
Processing a replay involves many steps. To start with, look at the `main` function of loop.py

## Processing tracking
The database table `job` contains a list of running jobs. Once a job has been finished it is removed from the `job` table. The status of the job can be retrieved from `replay.status` 

### Job status definitions
|status|definition|
|-|-|
|JOB_ADDED|Processing job added, awaiting processing|
|RECORDING|Launching Emulator and OBS|
|RECORDED|replay.mkv created by obs successfuly|
|MOVED|replay.mkv moved to `./finished/dirty_{replay.id}.mkv`|
|DESCRIPTION_CREATED| Description was created |
|BROKEN_CHECK| File was run though ffmpeg to fix a 'dirty' close |
|THUMBNAIL_CREATED| Thumbnail file was successfuly created |
|UPLOADED_TO_IA| File was successfuly uploaded to archive.org
|UPLOADED_TO_YOUTUBE| File was successfuly uploaded to youtube |
|REMOVED_GENERATED_FILES| Generated files were removed |
|FINISHED| Replay was processed successfuly |
|FAILED|An unhandled exception was generated |
