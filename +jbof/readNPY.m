function data = readNPY(filename)
%READNPY reads NPY files
%   READNPY(FILENAME) reads an NPY file FILENAME.
%
%   Only supports logical, (u)int{8,16,32,64}, float{32,64}, and
%   complex{64,128} NPY files. Timedelta, datetime, Python object,
%   zero-terminated strings, unicode strings, and void data are not
%   implemented.
%
%   Supported NPY versions are 1.0 and 2.0.
%
%   For a definition of NPY files, see:
%   http://www.numpy.org/neps/nep-0001-npy-format.html

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

    fid = fopen(filename, "rb");

    % read magic string:
    magic = fread(fid, 6, "uint8");
    if char(magic') ~= sprintf("\x93NUMPY")
        error(sprintf("%s is not a NumPy NPY file", filename));
    end

    % read version number:
    major = fread(fid, 1, "uint8");
    minor = fread(fid, 1, "uint8");
    if major == 1
        headerLen = fread(fid, 1, "uint16");
    elseif major == 2
        headerLen = fread(fid, 1, "uint32");
    else
        error(sprintf("Unsupported NPY version %i.%i", major, minor))
    end

    % read header dict:
    header = string(char(fread(fid, headerLen, "uint8")'));
    datatype = regexp(header, "['""]descr['""]:\s*['""]([<>]?)([?bBiufcmMOSaUV])([0-9]+)['""]", "tokens");
    datatype = string(datatype{1});
    % parse data type declaration, part I: endianness
    if datatype(1) == ">"
        endian = "b"; % big-endian
        datatype = datatype(2:end);
    elseif datatype(1) == "<"
        endian = "l"; % little-endian
        datatype = datatype(2:end);
    elseif datatype(1) == "="
        endian = "n"; % local machine format
        datatype = datatype(2:end);
    else
        endian = "n"; % local machine format
    end
    % parse data type declaration, part II: bitness
    if ~isnan(double(datatype(end)))
        numBytes = double(datatype(end));
        datatype = datatype(1:end-1);
    else
        numBytes = -1;
    end
    if length(datatype) ~= 1
        error(sprintf("unknown datatype %s", datatype))
    end
    % parse data type declaration, part III: encoding
    complexData = false;
    switch datatype
        case "?"
            datatype = "ubit1";
        case "b"
            datatype = "uint8";
        case "B"
            datatype = "int8";
        case "i"
            if numBytes < 0
                datatype = "int32";
            else
                datatype = "int" + numBytes*8;
            end
        case "u"
            if numBytes < 0
                datatype = "uint32";
            else
                datatype = "uint" + numBytes*8;
            end
        case "f"
            if numBytes < 0
                datatype = "float32";
            else
                datatype = "float" + numBytes*8;
            end
        case "c"
            complexData = true;
            if numBytes < 0
                datatype = "float32";
            else
                datatype = "float" + numBytes*4;
            end
        otherwise
            dict = struct("m", "timedelta", ...
                          "M", "datetime", ...
                          "O", "Python Object", ...
                          "S", "zero-terminated bytes", ...
                          "a", "zero-terminated bytes", ...
                          "U", "Unicode string", ...
                          "V", "void");
            error(sprintf("Format %s (%s) is not supported", datatype, dict(datatype)));
    end

    % read matrix order:
    fortranOrder = regexp(header, "['""]fortran_order['""]:\s*(False|True)", "tokens");
    fortranOrder = fortranOrder{1} == "True";

    % read data shape:
    shape = regexp(header, "['""]shape['""]:\s*\(([^\)]+)\)", "tokens");
    shape = split(shape{1}, ",");
    shape = double(shape(shape ~= ""));
    if length(shape) == 1
        shape(end+1) = 1;
    end

    % read data:
    numElements = prod(shape);
    if complexData
        numElements = numElements * 2;
    end
    data = fread(fid, numElements, datatype, 0, endian);
    if complexData
        data = data(1:2:end) + j*data(2:2:end);
    end
    fclose(fid);

    % reformat data correctly:
    if fortranOrder
        shape = fliplr(shape);
    end
    data = reshape(data, shape);
    if fortranOrder
        data = permute(data, length(size(x)):-1:1);
    end
end
