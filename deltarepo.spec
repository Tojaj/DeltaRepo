%global gitrev 98c23be
# gitrev is output of: git rev-parse --short HEAD

Name:           deltarepo
Summary:        Tool for generation and application of delta repositories.
Version:        0.0.1
Release:        1%{?dist}
License:        GPLv2
# Use the following commands to generate the tarball:
#  git clone https://github.com/Tojaj/DeltaRepo.git
#  cd DeltaRepo
#  utils/make_tarball.sh %{gitrev}
Source0:        deltarepo-%{gitrev}.tar.xz
URL:            https://github.com/Tojaj/DeltaRepo

BuildRequires:  cmake
BuildRequires:  python2
BuildRequires:  python-nose
BuildRequires:  python-lxml
BuildRequires:  python-createrepo_c
BuildRequires:  python-librepo
Requires:   python-deltarepo = %{version}-%{release}

%description
Set of tools that generate/merges differences between an old
and a new version of a repodata.

%package -n python-deltarepo
Summary:    Python library for generation and application of delta repositories.
Group:      Development/Languages
Requires:   %{name}%{?_isa} = %{version}-%{release}
Requires:   python-createrepo_c = %{version}-%{release}
Requires:   python-librepo
Requires:   python-lxml

%description -n python-deltarepo
Python library for generation and application of delta repositories.

%prep
%setup -q -n deltarepo

%build
%cmake .
make %{?_smp_mflags} RPM_OPT_FLAGS="$RPM_OPT_FLAGS"
#make doc

%check
make ARGS="-V" test

%install
make install DESTDIR=$RPM_BUILD_ROOT/

%files
%doc README.md
%doc LICENSE
#%_mandir/man8/createrepo_c.8.*
#%_mandir/man8/mergerepo_c.8.*
#%_mandir/man8/modifyrepo_c.8.*
#%config%{_sysconfdir}/bash_completion.d/deltarepo.bash
%{_bindir}/deltarepo
%{_bindir}/managedeltarepos
%{_bindir}/repocontenthash
%{_bindir}/repoupdater

%files -n python-deltarepo
%{python_sitearch}/deltarepo/

%changelog
* Tue Feb  25 2014 Tomas Mlcoch <tmlcoch at redhat.com> - 0.0.1-1
- Initial release
