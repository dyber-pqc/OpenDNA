class Opendna < Formula
  include Language::Python::Virtualenv

  desc "The People's Protein Engineering Platform"
  homepage "https://github.com/dyber-pqc/OpenDNA"
  url "https://files.pythonhosted.org/packages/source/o/opendna/opendna-0.5.0.tar.gz"
  sha256 "REPLACE_WITH_SHA"
  license "Apache-2.0"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    system bin/"opendna", "--version"
  end
end
