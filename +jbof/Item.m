classdef Item < handle
%Item is a collection of data arrays and metadata.
%
%   This class is not meant to be used manually, but only through
%   DataSet.

% Copyright (C) 2019 Bastian Bechtold
%
% This program is free software: you can redistribute it and/or modify
% it under the terms of the GNU General Public License as published by
% the Free Software Foundation, either version 3 of the License, or
% (at your option) any later version.
%
% This program is distributed in the hope that it will be useful, but
% WITHOUT ANY WARRANTY; without even the implied warranty of
% MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
% General Public License for more details.
%
% For the full text of the GNU General Public License, see
% <https://www.gnu.org/licenses/>.

    properties (Hidden)
        directory
        readonly
        metadataCache
    end

    properties (Dependent)
        metadata
        name
    end

    methods
        function obj = Item(directory, readonly)
            obj.directory = directory;
            obj.readonly = readonly;
            obj.metadataCache = [];
        end

        function metadata = get.metadata(obj)
            if ~isempty(obj.metadataCache)
                metadata = obj.metadataCache;
            else
                metadata = jsondecode(fileread(fullfile(obj.directory, "_metadata.json")));
                metadata = rmfield(metadata, "x_filename");
                obj.metadataCache = metadata;
            end
        end

        function name = get.name(obj)
            [~, name, ~] = fileparts(obj.directory);
        end

        function [data] = allArrays(obj)
            % Get a struct of all the data arrays and metadata in the Item
            data = struct();
            allFiles = dir(obj.directory);
            for fileIdx = 1:length(allFiles)
                file = allFiles(fileIdx);
                if endsWith(file.name, ".json") && string(file.name) ~= "_metadata.json"
                    baseName = extractBefore(file.name, ".json");
                    [array, metadata] = obj.getArray(baseName);
                    data.(baseName) = struct('array', array, ...
                                             'metadata', metadata);
                end
            end
        end

        function yesNo = hasArray(obj, name)
            % Check if data array of name exists.
            yesNo = isfile(fullfile(obj.directory, string(name) + ".json"));
        end

        function [array, metadata] = getArray(obj, name)
            % Get data array and metadata by name.
            if ~obj.hasArray(name)
                error(sprintf("No Array %s", name));
            end
            metadata = jsondecode(fileread(fullfile(obj.directory, string(name) + ".json")));
            filename = metadata.x_filename;
            metadata = rmfield(metadata, "x_filename");
            [~, ~, extension] = fileparts(filename);
            if extension == ".npy"
                array = jbof.readNPY(fullfile(obj.directory, string(name) + extension));
            elseif extension == ".wav" || extension == ".flac" || extension == ".ogg"
                [array, samplerate] = audioread(filename);
                metadata.samplerate = samplerate;
            elseif extension == ".mat"
                array = load(filename, name);
                array = array.(name);
            else
                error(sprintf("Unknown array file %d", filename));
            end
        end

        function yesNo = eq(obj, otherObj)
            yesNo = obj.directory == otherObj.directory;
        end

        %% Not implemented:

        function [array, metadata] = addArrayFromFile(obj, name, filename, metadata)
            error("Not implemented")
        end

        function [array, metadata] = addArray(obj, name, data, metadata, fileformat, samplerate)
            error("Not implemented")
        end

        function deleteArray(obj, array)
            error("Not implemented")
        end

        function hash = hash(obj)
            error("Not implemented")
        end

    end
end
