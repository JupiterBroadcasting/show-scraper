# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.provider "libvirt" do |lv,override|
    override.vm.box = "generic/ubuntu2204"
    override.vm.synced_folder ".", "/vagrant/"
  end
  config.vm.box = "bento/ubuntu-22.04"
  config.vm.provision "shell", inline: <<-SHELL
    export DEBIAN_FRONTEND='noninteractive'
    apt-get update &&
      apt-get install -y python3-pip &&
      pip3 install pipenv
  SHELL
end
