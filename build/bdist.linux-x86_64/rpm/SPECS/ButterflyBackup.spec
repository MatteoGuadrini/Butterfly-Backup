%define name ButterflyBackup
%define version 1.0.0
%define unmangled_version 1.0.0
%define unmangled_version 1.0.0
%define release 1.0.0

Summary: Butterfly Backup is a simple wrapper of rsync written in python
Name: %{name}
Version: %{version}
Release: %{release}
Source0: %{name}-%{unmangled_version}.tar.gz
License: GPLv3
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Matteo Guadrini <matteo.guadrini@hotmail.it>
Packager: Matteo Guadrini <matteo.guadrini@hotmail.it>
Provides: backup restore archive
Url: https://matteoguadrini.github.io/Butterfly-Backup
Distribution: fedora
BuildRequires: rsync openssh

%description
UNKNOWN

%prep
%setup -n %{name}-%{unmangled_version} -n %{name}-%{unmangled_version}

%build
python3 setup.py build

%install
python3 setup.py install --single-version-externally-managed -O1 --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

%clean
rm -rf $RPM_BUILD_ROOT

%files -f INSTALLED_FILES
%defattr(-,root,root)
