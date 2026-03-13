BEGIN;

DELETE FROM communities_files
WHERE object_version_id IN (
    SELECT fo.version_id FROM files_object fo
    JOIN files_files ff ON fo.file_id = ff.id
    WHERE ff.uri LIKE 'file:%'
);

DELETE FROM rdm_drafts_files
WHERE object_version_id IN (
    SELECT fo.version_id FROM files_object fo
    JOIN files_files ff ON fo.file_id = ff.id
    WHERE ff.uri LIKE 'file:%'
);

DELETE FROM rdm_drafts_media_files
WHERE object_version_id IN (
    SELECT fo.version_id FROM files_object fo
    JOIN files_files ff ON fo.file_id = ff.id
    WHERE ff.uri LIKE 'file:%'
);

DELETE FROM rdm_records_files
WHERE object_version_id IN (
    SELECT fo.version_id FROM files_object fo
    JOIN files_files ff ON fo.file_id = ff.id
    WHERE ff.uri LIKE 'file:%'
);

DELETE FROM rdm_records_media_files
WHERE object_version_id IN (
    SELECT fo.version_id FROM files_object fo
    JOIN files_files ff ON fo.file_id = ff.id
    WHERE ff.uri LIKE 'file:%'
);

DELETE FROM request_files
WHERE object_version_id IN (
    SELECT fo.version_id FROM files_object fo
    JOIN files_files ff ON fo.file_id = ff.id
    WHERE ff.uri LIKE 'file:%'
);

DELETE FROM files_object
WHERE file_id IN (
    SELECT id FROM files_files WHERE uri LIKE 'file:%'
);

DELETE FROM files_files
WHERE uri LIKE 'file:%';

COMMIT;
