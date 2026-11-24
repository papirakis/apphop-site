# Source from other scripts. Loads Fastly/Bunny credentials from chmod 600 files
# under ~/.fastly-secure and ~/.bunny-secure. Never echo, print, or log values.
# Usage:  . /path/to/scripts/cdn_env.sh
[ -f "${HOME}/.fastly-secure/fastly.env" ] && . "${HOME}/.fastly-secure/fastly.env"
[ -f "${HOME}/.bunny-secure/bunny.env" ] && . "${HOME}/.bunny-secure/bunny.env"
if [ -z "${FASTLY_API_KEY:-}" ] && [ -n "${FASTLY_API_TOKEN:-}" ]; then
  FASTLY_API_KEY="${FASTLY_API_TOKEN}"
  export FASTLY_API_KEY
fi
export FASTLY_API_TOKEN FASTLY_API_KEY FASTLY_SERVICE_ID
export BUNNY_API_KEY BUNNY_STORAGE_ZONE BUNNY_STORAGE_HOST BUNNY_STORAGE_PASSWORD BUNNY_PULLZONE_ID
