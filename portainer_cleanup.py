import urllib.request, json, ssl, time

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

PORTAINER = 'https://192.168.4.67:9443'

# Get token
data = json.dumps({'Username':'admin','Password':'Lumayanrahasia3'}).encode()
req = urllib.request.Request(PORTAINER+'/api/auth', data=data, headers={'Content-Type':'application/json'})
resp = urllib.request.urlopen(req, timeout=10, context=ctx)
token = json.loads(resp.read())['jwt']
headers = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}
print('Portainer auth: OK')

# Check volumes / nodes info - get disk info
req2 = urllib.request.Request(PORTAINER+'/api/endpoints/1/docker/info', headers=headers)
resp2 = urllib.request.urlopen(req2, timeout=10, context=ctx)
info = json.loads(resp2.read())
print('\n=== Docker Info ===')
print('DockerRootDir:', info.get('DockerRootDir'))
print('MemTotal:', round(info.get('MemTotal',0)/1024/1024/1024, 2), 'GB')

# Check disk usage via docker system df API
req3 = urllib.request.Request(PORTAINER+'/api/endpoints/1/docker/system/df', headers=headers)
resp3 = urllib.request.urlopen(req3, timeout=10, context=ctx)
df = json.loads(resp3.read())

images = df.get('Images', [])
print(f'\n=== Docker Images ({len(images)} total) ===')
total_size = 0
for img in sorted(images, key=lambda x: x.get('Size', 0), reverse=True)[:10]:
    tags = img.get('RepoTags') or ['<none>']
    size_mb = img.get('Size', 0) // 1024 // 1024
    total_size += img.get('Size', 0)
    print(f'  {size_mb}MB - {tags[0]}')
print(f'Total image size: {total_size//1024//1024}MB')

containers = df.get('Containers', [])
print(f'\n=== Containers ({len(containers)}) ===')
for c in containers:
    names = c.get('Names', ['?'])
    print(f'  {c.get("State")} - {names[0] if names else "?"} - {c.get("Status")}')

# Docker prune - remove dangling images
print('\n=== Running docker image prune ===')
data_prune = json.dumps({}).encode()
req_prune = urllib.request.Request(
    PORTAINER+'/api/endpoints/1/docker/images/prune',
    data=data_prune,
    headers=headers,
    method='POST'
)
resp_prune = urllib.request.urlopen(req_prune, timeout=30, context=ctx)
prune_result = json.loads(resp_prune.read())
reclaimed = prune_result.get('SpaceReclaimed', 0)
print(f'Images pruned: {len(prune_result.get("ImagesDeleted") or [])} | Space reclaimed: {reclaimed//1024//1024}MB')
