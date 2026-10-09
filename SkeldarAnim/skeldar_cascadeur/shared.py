"""Send an animation FBX to everybody, the way Maya's Shared card sends a file:
zip it, announce it as `sending`, upload (temp.sh, then litterbox), announce
`ready` with the address. A failure announces `failed` and re-raises.

Stdlib plus the two share modules. No Maya, no Cascadeur.
"""

import os
import tempfile
import time
import zipfile

import maya_sharenet
import maya_sharerecords as records


def zip_fbx(path, name, folder=None):
    """A zip holding `path` under the member name `name`. The caller removes it."""
    handle, archive = tempfile.mkstemp(prefix="skeldar_cascade_", suffix=".zip",
                                       dir=folder)
    os.close(handle)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as out:
        out.write(path, name)
    return archive


def send(path, name, author, machine, net=None, now=None, progress=None):
    """Upload `path` as `name`; the ready record (with `url` and `zip`).

    `net` and `now` are injectable for the tests. Raises the net's ShareError
    after publishing `failed`, so the colleagues drop the row.
    """
    net = net or maya_sharenet
    clock = now or time.time
    rid = records.new_id()
    size = os.path.getsize(path)
    record = records.make_record("sending", rid, author, machine, name, size,
                                 int(clock()))
    net.publish(records.encode(record))
    archive = zip_fbx(path, name)
    try:
        zipped = os.path.getsize(archive)
        if zipped > records.MAX_ZIP:
            raise net.ShareError("the zip is {0} bytes, over the hosts' 1 GB"
                                 .format(zipped))
        url = net.upload_any(archive, progress=progress)
        ready = records.with_state(record, "ready", url=url, zip=zipped)
        net.publish(records.encode(ready))
        return ready
    except Exception:
        try:
            net.publish(records.encode(records.with_state(record, "failed")))
        except Exception:
            pass
        raise
    finally:
        if os.path.exists(archive):
            os.remove(archive)
